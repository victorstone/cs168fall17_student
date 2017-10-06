"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16

class Route:
    def __init__(self, distance, port, time):
        self.distance = distance
        self.port = port
        self.time = time

    def get_distance(self):
        return self.distance

    def get_port(self):
        return self.port

    def get_time(self):
        return self.time

    def update_distance(self, new_distance):
        self.distance = new_distance

    def update_time(self, new_time):
        self.time = new_time


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
        self.port_latency_map = {}
        self.host_route_map = {}
        self.poisoned_route_map = {}

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.port_latency_map[port] = latency
        for host in self.host_route_map:
            self.send(basics.RoutePacket(host, self.host_route_map[host].get_distance()), port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        for host in self.host_route_map:
            val = self.host_route_map[host]
            if val and val.get_port() == port:
                if self.POISON_MODE:
                    self.poisoned_route_map[host] = val
                    self.send(basics.RoutePacket(host, INFINITY), flood=True)
                self.host_route_map[host] = None

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())
        if isinstance(packet, basics.RoutePacket):
            if packet.latency + self.port_latency_map[port] < INFINITY:
                new_dist = packet.latency + self.port_latency_map[port];
                if self.POISON_MODE:
                    if packet.destination in self.poisoned_route_map:
                        del self.poisoned_route_map[packet.destination]
                    self.send(basics.RoutePacket(packet.destination, INFINITY), port)

                if packet.destination not in self.host_route_map.keys() or self.host_route_map[packet.destination] is \
                        None or self.host_route_map[packet.destination].get_distance() > new_dist:
                    self.host_route_map[packet.destination] = \
                        Route(self.port_latency_map[port] + packet.latency, port, api.current_time())
                    self.send(basics.RoutePacket(packet.destination, new_dist), port,flood=True)

                else:
                    if new_dist == self.host_route_map[packet.destination].get_distance():
                        if self.host_route_map[packet.destination].get_time() < api.current_time():
                            self.host_route_map[packet.destination] = Route(new_dist, port, api.current_time())
                            self.send(basics.RoutePacket(packet.destination, new_dist), port, flood=True)
                    if self.host_route_map[packet.destination].get_port() == port:
                        if new_dist > self.host_route_map[packet.destination].get_distance():
                            self.host_route_map[packet.destination].update_distance(new_dist)
                            self.send(basics.RoutePacket(packet.destination, new_dist), port, flood=True)
                        self.host_route_map[packet.destination].update_time(api.current_time())

            elif packet.latency >= INFINITY and self.POISON_MODE:
                for host in self.host_route_map:
                    if host == packet.destination:
                        if self.host_route_map[host] and self.host_route_map[host].get_port() == port:
                            self.send(basics.RoutePacket(packet.destination, INFINITY), port, flood=True)
                            self.poisoned_route_map[host] = self.host_route_map[host]
                            self.host_route_map[host] = None

        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.host_route_map[packet.src] = Route(self.port_latency_map[port], port, -1)
            self.send(basics.RoutePacket(packet.src, self.port_latency_map[port]), port, flood=True)

        else:
            # ping
            if packet.dst in self.host_route_map:
                host = self.host_route_map[packet.dst]
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
            for p in self.poisoned_route_map:
                self.send(basics.RoutePacket(p, INFINITY), flood=True)
        for host in self.host_route_map:
            if self.host_route_map[host]:
                route_has_not_expired = api.current_time() - self.host_route_map[host].get_time() <= self.ROUTE_TIMEOUT
                host_route = False
                if self.host_route_map[host].get_time() == -1:
                    host_route = True
                if route_has_not_expired or host_route:
                    self.update_neighbor(host)
                else:
                    self.expired_routes_update(host)

    def update_neighbor(self, host):
        if self.POISON_MODE:
            self.send(basics.RoutePacket(host, INFINITY), self.host_route_map[host].get_port())
        self.send(basics.RoutePacket(host, self.host_route_map[host].get_distance()),
                  self.host_route_map[host].get_port(), flood=True)

    def expired_routes_update(self, host):
        if self.POISON_MODE:
            self.send(basics.RoutePacket(host, INFINITY), self.host_route_map[host].get_port())
            self.poisoned_route_map[host] = self.host_route_map[host]
        self.host_route_map[host] = None
