class Node(object):

    def __init__(self, query, results):
        self.query = query
        self.results = results
        self.prev = None
        self.next = None


class LinkedList(object):

    def __init__(self):
        self.head = None
        self.tail = None

    def move_to_front(self, node):
        if node is self.head:
            return
        self._detach(node)
        self.append_to_front(node)

    def append_to_front(self, node):
        node.prev = None
        node.next = self.head
        if self.head:
            self.head.prev = node
        self.head = node
        if self.tail is None:
            self.tail = node

    def remove_from_tail(self):
        if self.tail is None:
            return None
        old_tail = self.tail
        self._detach(old_tail)
        return old_tail

    def _detach(self, node):
        if node.prev:
            node.prev.next = node.next
        if node.next:
            node.next.prev = node.prev
        if node is self.tail:
            self.tail = node.prev
        if node is self.head:
            self.head = node.next
        node.prev = None
        node.next = None


class Cache(object):

    def __init__(self, max_size):
        if max_size <= 0:
            raise ValueError('max_size must be positive')
        self.max_size = max_size
        self.size = 0
        self.lookup = {}  # key: query, value: node
        self.linked_list = LinkedList()

    def get(self, query):
        """Get the stored query result from the cache.

        Accessing a node updates its position to the front of the LRU list.
        """
        node = self.lookup.get(query)
        if node is None:
            return None
        self.linked_list.move_to_front(node)
        return node.results

    def set(self, results, query):
        """Set the result for the given query key in the cache.

        When updating an entry, updates its position to the front of the LRU list.
        If the entry is new and the cache is at capacity, removes the oldest entry
        before the new entry is added.
        """
        node = self.lookup.get(query)
        if node is not None:
            # Key exists in cache, update the value
            node.results = results
            self.linked_list.move_to_front(node)
            return

        # Key does not exist in cache
        if self.size == self.max_size:
            # Remove the oldest entry from the linked list and lookup
            lru_node = self.linked_list.remove_from_tail()
            if lru_node:
                self.lookup.pop(lru_node.query, None)
        else:
            self.size += 1
        # Add the new key and value
        new_node = Node(query, results)
        self.linked_list.append_to_front(new_node)
        self.lookup[query] = new_node
