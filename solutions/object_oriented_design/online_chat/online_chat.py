from abc import ABCMeta
from datetime import datetime
from enum import Enum


class UserService(object):

    def __init__(self):
        self.users_by_id = {}  # key: user id, value: User
        self.private_chats_by_pair = {}  # key: frozenset(user ids), value: PrivateChat
        self.next_group_chat_id = 1

    def add_user(self, user_id, name, pass_hash):
        if user_id in self.users_by_id:
            raise ValueError('User already exists: {}'.format(user_id))
        user = User(user_id, name, pass_hash)
        self.users_by_id[user_id] = user
        return user

    def remove_user(self, user_id):
        user = self.users_by_id.pop(user_id, None)
        if user is None:
            return
        # Clean up friendships
        for friend_id, friend in list(user.friends_by_id.items()):
            friend.friends_by_id.pop(user_id, None)
            friend.friend_ids_to_private_chats.pop(user_id, None)
        # Remove pending requests
        for friend_id, friend in list(self.users_by_id.items()):
            friend.received_friend_requests_by_friend_id.pop(user_id, None)
            friend.sent_friend_requests_by_friend_id.pop(user_id, None)
        # Remove private chats for this user
        for pair in list(self.private_chats_by_pair.keys()):
            if user_id in pair:
                self.private_chats_by_pair.pop(pair, None)

    def add_friend_request(self, from_user_id, to_user_id):
        from_user = self.users_by_id[from_user_id]
        to_user = self.users_by_id[to_user_id]
        from_user.send_friend_request(to_user)

    def approve_friend_request(self, from_user_id, to_user_id):
        from_user = self.users_by_id[from_user_id]
        to_user = self.users_by_id[to_user_id]
        to_user.approve_friend_request(from_user)
        self._ensure_private_chat(from_user, to_user)

    def reject_friend_request(self, from_user_id, to_user_id):
        from_user = self.users_by_id[from_user_id]
        to_user = self.users_by_id[to_user_id]
        to_user.reject_friend_request(from_user)
        from_user.reject_friend_request(to_user)

    def _ensure_private_chat(self, first_user, second_user):
        pair_key = frozenset((first_user.user_id, second_user.user_id))
        if pair_key not in self.private_chats_by_pair:
            chat_id = 'private-{}-{}'.format(min(pair_key), max(pair_key))
            chat = PrivateChat(chat_id, first_user, second_user)
            self.private_chats_by_pair[pair_key] = chat
            first_user.friend_ids_to_private_chats[second_user.user_id] = chat
            second_user.friend_ids_to_private_chats[first_user.user_id] = chat
        return self.private_chats_by_pair[pair_key]


class User(object):

    def __init__(self, user_id, name, pass_hash):
        self.user_id = user_id
        self.name = name
        self.pass_hash = pass_hash
        self.friends_by_id = {}  # key: friend id, value: User
        self.friend_ids_to_private_chats = {}  # key: friend id, value: private chats
        self.group_chats_by_id = {}  # key: chat id, value: GroupChat
        self.received_friend_requests_by_friend_id = {}  # key: friend id, value: AddRequest
        self.sent_friend_requests_by_friend_id = {}  # key: friend id, value: AddRequest

    def message_user(self, friend_id, message):
        if friend_id not in self.friends_by_id:
            raise ValueError('Cannot message non-friend: {}'.format(friend_id))
        chat = self.friend_ids_to_private_chats.get(friend_id)
        if chat is None:
            friend = self.friends_by_id[friend_id]
            chat_id = 'private-{}-{}'.format(min(self.user_id, friend_id), max(self.user_id, friend_id))
            chat = PrivateChat(chat_id, self, friend)
            self.friend_ids_to_private_chats[friend_id] = chat
            friend.friend_ids_to_private_chats[self.user_id] = chat
        message_id = len(chat.messages) + 1
        msg = Message(message_id, message, datetime.utcnow())
        chat.messages.append(msg)
        return msg

    def message_group(self, group_id, message):
        group_chat = self.group_chats_by_id.get(group_id)
        if group_chat is None:
            raise ValueError('User is not a member of group {}'.format(group_id))
        message_id = len(group_chat.messages) + 1
        msg = Message(message_id, message, datetime.utcnow())
        group_chat.messages.append(msg)
        return msg

    def send_friend_request(self, friend):
        if friend.user_id in self.friends_by_id:
            return None
        if friend.user_id in self.sent_friend_requests_by_friend_id:
            return self.sent_friend_requests_by_friend_id[friend.user_id]
        request = AddRequest(self.user_id, friend.user_id, RequestStatus.UNREAD, datetime.utcnow())
        self.sent_friend_requests_by_friend_id[friend.user_id] = request
        friend.received_friend_requests_by_friend_id[self.user_id] = request
        return request

    def receive_friend_request(self, friend):
        if friend.user_id in self.friends_by_id:
            return None
        existing = self.received_friend_requests_by_friend_id.get(friend.user_id)
        if existing:
            return existing
        request = AddRequest(friend.user_id, self.user_id, RequestStatus.UNREAD, datetime.utcnow())
        self.received_friend_requests_by_friend_id[friend.user_id] = request
        friend.sent_friend_requests_by_friend_id[self.user_id] = request
        return request

    def approve_friend_request(self, friend):
        request = self.received_friend_requests_by_friend_id.get(friend.user_id)
        if request is None:
            return None
        request.request_status = RequestStatus.ACCEPTED
        self.received_friend_requests_by_friend_id.pop(friend.user_id, None)
        friend.sent_friend_requests_by_friend_id.pop(self.user_id, None)
        self.friends_by_id[friend.user_id] = friend
        friend.friends_by_id[self.user_id] = self
        return request

    def reject_friend_request(self, friend):
        request = self.received_friend_requests_by_friend_id.get(friend.user_id)
        if request is None:
            return None
        request.request_status = RequestStatus.REJECTED
        self.received_friend_requests_by_friend_id.pop(friend.user_id, None)
        friend.sent_friend_requests_by_friend_id.pop(self.user_id, None)
        return request


class Chat(metaclass=ABCMeta):

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.users = []
        self.messages = []


class PrivateChat(Chat):

    def __init__(self, chat_id, first_user, second_user):
        super(PrivateChat, self).__init__(chat_id)
        self.users.append(first_user)
        self.users.append(second_user)


class GroupChat(Chat):

    def add_user(self, user):
        if user not in self.users:
            self.users.append(user)
            user.group_chats_by_id[self.chat_id] = self

    def remove_user(self, user):
        if user in self.users:
            self.users.remove(user)
            user.group_chats_by_id.pop(self.chat_id, None)


class Message(object):

    def __init__(self, message_id, message, timestamp):
        self.message_id = message_id
        self.message = message
        self.timestamp = timestamp


class AddRequest(object):

    def __init__(self, from_user_id, to_user_id, request_status, timestamp):
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.request_status = request_status
        self.timestamp = timestamp


class RequestStatus(Enum):

    UNREAD = 0
    READ = 1
    ACCEPTED = 2
    REJECTED = 3
