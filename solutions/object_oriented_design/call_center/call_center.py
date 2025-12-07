from abc import ABCMeta, abstractmethod
from collections import deque
from enum import Enum


class Rank(Enum):

    OPERATOR = 0
    SUPERVISOR = 1
    DIRECTOR = 2


class Employee(metaclass=ABCMeta):

    def __init__(self, employee_id, name, rank, call_center=None):
        self.employee_id = employee_id
        self.name = name
        self.rank = rank
        self.call = None
        self.call_center = call_center

    def take_call(self, call):
        """Assume the employee will always successfully take the call."""
        self.call = call
        self.call.employee = self
        self.call.state = CallState.IN_PROGRESS

    def complete_call(self):
        if self.call is None:
            return
        self.call.state = CallState.COMPLETE
        completed_call = self.call
        self.call = None
        self.call_center.notify_call_completed(completed_call)

    @abstractmethod
    def escalate_call(self):
        pass

    def _escalate_call(self):
        if self.call is None:
            return
        self.call.state = CallState.READY
        call = self.call
        self.call = None
        call.employee = None
        self.call_center.notify_call_escalated(call)


class Operator(Employee):

    def __init__(self, employee_id, name, call_center=None):
        super(Operator, self).__init__(employee_id, name, Rank.OPERATOR, call_center)

    def escalate_call(self):
        self.call.rank = Rank.SUPERVISOR
        self._escalate_call()


class Supervisor(Employee):

    def __init__(self, employee_id, name, call_center=None):
        super(Supervisor, self).__init__(employee_id, name, Rank.SUPERVISOR, call_center)

    def escalate_call(self):
        self.call.rank = Rank.DIRECTOR
        self._escalate_call()


class Director(Employee):

    def __init__(self, employee_id, name, call_center=None):
        super(Director, self).__init__(employee_id, name, Rank.DIRECTOR, call_center)

    def escalate_call(self):
        raise NotImplementedError('Directors must be able to handle any call')


class CallState(Enum):

    READY = 0
    IN_PROGRESS = 1
    COMPLETE = 2


class Call(object):

    def __init__(self, rank):
        self.state = CallState.READY
        self.rank = rank
        self.employee = None


class CallCenter(object):

    def __init__(self, operators, supervisors, directors):
        self.operators = operators
        self.supervisors = supervisors
        self.directors = directors
        self.queued_calls = deque()
        for employee in self.operators + self.supervisors + self.directors:
            employee.call_center = self

    def dispatch_call(self, call):
        if call.rank not in (Rank.OPERATOR, Rank.SUPERVISOR, Rank.DIRECTOR):
            raise ValueError('Invalid call rank: {}'.format(call.rank))
        employee = None
        if call.rank == Rank.OPERATOR:
            employee = self._dispatch_call(call, self.operators)
        if call.rank == Rank.SUPERVISOR or employee is None:
            employee = self._dispatch_call(call, self.supervisors)
        if call.rank == Rank.DIRECTOR or employee is None:
            employee = self._dispatch_call(call, self.directors)
        if employee is None:
            self.queued_calls.append(call)
        return employee

    def _dispatch_call(self, call, employees):
        for employee in employees:
            if employee.call is None:
                employee.take_call(call)
                return employee
        return None

    def notify_call_escalated(self, call):
        self.dispatch_call(call)

    def notify_call_completed(self, call):
        employee = call.employee
        call.employee = None
        if employee is not None:
            employee.call = None
            self.dispatch_queued_call_to_newly_freed_employee(employee)

    def dispatch_queued_call_to_newly_freed_employee(self, employee):
        if employee is None:
            return None
        for queued_call in list(self.queued_calls):
            if employee.rank.value >= queued_call.rank.value:
                employee.take_call(queued_call)
                self.queued_calls.remove(queued_call)
                return queued_call
        return None
