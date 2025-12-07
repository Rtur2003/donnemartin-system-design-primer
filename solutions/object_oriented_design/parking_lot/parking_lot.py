from abc import ABCMeta, abstractmethod
from enum import Enum


class VehicleSize(Enum):

    MOTORCYCLE = 0
    COMPACT = 1
    LARGE = 2


class Vehicle(metaclass=ABCMeta):

    def __init__(self, vehicle_size, license_plate, spot_size):
        self.vehicle_size = vehicle_size
        self.license_plate = license_plate
        self.spot_size = spot_size
        self.spots_taken = []

    def clear_spots(self):
        for spot in self.spots_taken:
            spot.remove_vehicle()
        self.spots_taken = []

    def take_spot(self, spot):
        self.spots_taken.append(spot)

    @abstractmethod
    def can_fit_in_spot(self, spot):
        pass


class Motorcycle(Vehicle):

    def __init__(self, license_plate):
        super(Motorcycle, self).__init__(VehicleSize.MOTORCYCLE, license_plate, spot_size=1)

    def can_fit_in_spot(self, spot):
        return True


class Car(Vehicle):

    def __init__(self, license_plate):
        super(Car, self).__init__(VehicleSize.COMPACT, license_plate, spot_size=1)

    def can_fit_in_spot(self, spot):
        return spot.vehicle_size in (VehicleSize.LARGE, VehicleSize.COMPACT)


class Bus(Vehicle):

    def __init__(self, license_plate):
        super(Bus, self).__init__(VehicleSize.LARGE, license_plate, spot_size=5)

    def can_fit_in_spot(self, spot):
        return spot.vehicle_size == VehicleSize.LARGE


class ParkingLot(object):

    def __init__(self, num_levels):
        self.num_levels = num_levels
        self.levels = [Level(floor, Level.SPOTS_PER_ROW * 5) for floor in range(num_levels)]

    def park_vehicle(self, vehicle):
        for level in self.levels:
            if level.park_vehicle(vehicle):
                return True
        return False


class Level(object):

    SPOTS_PER_ROW = 10

    def __init__(self, floor, total_spots):
        self.floor = floor
        self.num_spots = total_spots
        self.available_spots = total_spots
        self.spots = []  # List of ParkingSpots
        self._init_spots(total_spots)

    def _init_spots(self, total_spots):
        """Initialize rows of spots with a simple distribution across sizes."""
        for spot_number in range(total_spots):
            row = spot_number // self.SPOTS_PER_ROW
            if spot_number < total_spots * 0.25:
                size = VehicleSize.MOTORCYCLE
            elif spot_number < total_spots * 0.5:
                size = VehicleSize.COMPACT
            else:
                size = VehicleSize.LARGE
            self.spots.append(ParkingSpot(self, row, spot_number, 1, size))

    def spot_freed(self):
        self.available_spots += 1

    def park_vehicle(self, vehicle):
        spot = self._find_available_spot(vehicle)
        if spot is None:
            return None
        else:
            if vehicle.spot_size > 1:
                self._park_starting_at_spot(spot, vehicle)
            else:
                spot.park_vehicle(vehicle)
            return spot

    def _find_available_spot(self, vehicle):
        """Find an available spot where vehicle can fit, or return None"""
        if vehicle.spot_size == 1:
            for spot in self.spots:
                if spot.can_fit_vehicle(vehicle):
                    return spot
            return None

        consecutive = []
        current_row = None
        for spot in self.spots:
            if current_row is None or spot.row != current_row:
                consecutive = []
                current_row = spot.row
            if spot.can_fit_vehicle(vehicle):
                consecutive.append(spot)
                if len(consecutive) == vehicle.spot_size:
                    return consecutive[0]
            else:
                consecutive = []
        return None

    def _park_starting_at_spot(self, spot, vehicle):
        """Occupy starting at spot.spot_number to vehicle.spot_size."""
        start_index = self.spots.index(spot)
        for index in range(start_index, start_index + vehicle.spot_size):
            self.spots[index].park_vehicle(vehicle)


class ParkingSpot(object):

    def __init__(self, level, row, spot_number, spot_size, vehicle_size):
        self.level = level
        self.row = row
        self.spot_number = spot_number
        self.spot_size = spot_size
        self.vehicle_size = vehicle_size
        self.vehicle = None

    def is_available(self):
        return True if self.vehicle is None else False

    def can_fit_vehicle(self, vehicle):
        if self.vehicle is not None:
            return False
        return vehicle.can_fit_in_spot(self)

    def park_vehicle(self, vehicle):
        if not self.can_fit_vehicle(vehicle):
            return False
        self.vehicle = vehicle
        vehicle.take_spot(self)
        self.level.available_spots -= 1
        return True

    def remove_vehicle(self):
        if self.vehicle:
            vehicle = self.vehicle
            self.vehicle = None
            self.level.spot_freed()
            if self in vehicle.spots_taken:
                vehicle.spots_taken.remove(self)
            return vehicle
        return None
