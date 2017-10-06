"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16


class Route:
    def __init__(self, distance, port, time):
        self._distance = distance
        self._port = port
        self._time = time

    def get_distance(self):
        return self._distance

    def get_port(self):
        return self._port

    def get_time(self):
        return self._time

    def update_distance(self, new_distanceance):
        self._distance = new_distanceance

    def update_time(self, new_time):
        self._time = new_time


class RoutingData:
    def __init__(self):
        self._port_latency_map = {}
        self._host_route_map = {}
        self._poisoned_route_map = {}

    def set_port_latency(self, port, latency):
        self._port_latency_map[port] = latency

    def get_port_latency(self, port):
        if port in self._port_latency_map:
            return self._port_latency_map[port]
        return None

    def get_port_latency_map(self):
        return self._port_latency_map

    def set_route(self, host, distance, port, time):
        new_route = Route(distance, port, time)
        self._host_route_map[host] = new_route

    def update_route_distance(self, host, distance):
        self._host_route_map[host].update_distance(distance)

    def update_route_time(self, host, time):
        self._host_route_map[host].update_time(time)

    def get_route(self, host):
        if host in self._host_route_map:
            return self._host_route_map[host]
        return None

    def null_route(self, host):
        if host in self._host_route_map:
            self._host_route_map[host] = None

    def get_host_route_map(self):
        return self._host_route_map

    def get_poisoned_route(self, host):
        if host in self._poisoned_route_map:
            return self._poisoned_route_map[host]
        return None

    def get_poisoned_route_map(self):
        return self._poisoned_route_map

    def set_poisoned_route(self, host, route):
        self._poisoned_route_map[host] = route

    def delete_poisoned_route(self, host):
        if host in self._poisoned_route_map:
            del self._poisoned_route_map[host]


class DVRouter(basics.DVRouterBase):
    NO_LOG = True # Set to True on an instance to disable its logging
    POISON_MODE = True # Can override POISON_MODE here
    DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.start_timer()  # Starts calling handle_timer() at correct rate
        self.routing_data = RoutingData()

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.routing_data.set_port_latency(port, latency)
        for host in self.routing_data.get_host_route_map():
            route = self.routing_data.get_route(host)
            if route:
                self.send(basics.RoutePacket(host, route.get_distance()), port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        for host in self.routing_data.get_host_route_map():
            val = self.routing_data.get_route(host)
            if val and val.get_port() == port:
                if self.POISON_MODE:
                    self.routing_data.set_poisoned_route(host, val)
                    self.send(basics.RoutePacket(host, INFINITY), flood=True)
                self.routing_data.null_route(host)

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())

        if isinstance(packet, basics.RoutePacket):
            new_distance = packet.latency + self.routing_data.get_port_latency(port)
            if new_distance < INFINITY:
                if self.POISON_MODE:
                    if self.routing_data.get_poisoned_route(packet.destination):
                        self.routing_data.delete_poisoned_route(packet.destination)
                    self.send(basics.RoutePacket(packet.destination, INFINITY), port)

                if self.routing_data.get_route(packet.destination) is None or \
                        self.routing_data.get_route(packet.destination).get_distance() > new_distance:
                    self.routing_data.set_route(packet.destination, self.routing_data.get_port_latency(port) +
                                                packet.latency, port, api.current_time())
                    self.send(basics.RoutePacket(packet.destination, new_distance), port, flood=True)

                else:
                    route = self.routing_data.get_route(packet.destination)
                    if new_distance == route.get_distance():
                        if route.get_time() < api.current_time():
                            self.routing_data.set_route(packet.destination, new_distance, port, api.current_time())
                            self.send(basics.RoutePacket(packet.destination, new_distance), port, flood=True)
                    if route.get_port() == port:
                        if new_distance > route.get_distance():
                            self.routing_data.update_route_distance(packet.destination, new_distance)
                            self.send(basics.RoutePacket(packet.destination, new_distance), port, flood=True)
                        self.routing_data.update_route_time(packet.destination, api.current_time())

            elif packet.latency >= INFINITY and self.POISON_MODE:
                for host in self.routing_data.get_host_route_map():
                    if host == packet.destination:
                        if self.routing_data.get_route(host) and self.routing_data.get_route(host).get_port() == port:
                            self.send(basics.RoutePacket(packet.destination, INFINITY), port, flood=True)
                            self.routing_data.set_poisoned_route(host, self.routing_data.get_route(host))
                            self.routing_data.null_route(host)

        elif isinstance(packet, basics.HostDiscoveryPacket):
            latency = self.routing_data.get_port_latency(port)
            self.routing_data.set_route(packet.src, latency, port, -1)
            self.send(basics.RoutePacket(packet.src, latency), port, flood=True)

        else:
            # ping
            if packet.dst in self.routing_data.get_host_route_map():
                host = self.routing_data.get_route(packet.dst)
                if host is not None and host.get_port() != port and host.get_distance() <= INFINITY:
                    self.send(packet, host.get_port(), flood=False)

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        if self.POISON_MODE:
            for p_route in self.routing_data.get_poisoned_route_map():
                self.send(basics.RoutePacket(p_route, INFINITY), flood=True)
        for host in self.routing_data.get_host_route_map():
            route = self.routing_data.get_route(host)
            if route:
                time_diff = api.current_time() - route.get_time()
                if route.get_time() == -1 or time_diff <= self.ROUTE_TIMEOUT:
                    if self.POISON_MODE:
                        self.send(basics.RoutePacket(host, INFINITY), route.get_port())
                    self.send(basics.RoutePacket(host, route.get_distance()), route.get_port(),
                              flood=True)
                else:
                    if self.POISON_MODE:
                        self.send(basics.RoutePacket(host, INFINITY), route.get_port())
                        self.routing_data.set_poisoned_route(host, route)
                    self.routing_data.null_route(host)

