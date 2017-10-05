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
        pass

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())
        if isinstance(packet, basics.RoutePacket):
            pass
        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.host_route_map[packet.src] = Route(self.port_latency_map[port], port, None)
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
        pass
