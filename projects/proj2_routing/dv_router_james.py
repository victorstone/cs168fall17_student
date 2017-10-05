"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True # Set to True on an instance to disable its logging
    # POISON_MODE = True # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.start_timer()  # Starts calling handle_timer() at correct rate
        self.host_to_route = {} #host to [dist, port, time]
        self.port_to_latency = {} #port to latency
        self.poison_state = {} 

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.port_to_latency[port] = latency
        for host in self.host_to_route.keys():
            self.send(basics.RoutePacket(host, self.host_to_route[host][0]), port)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        if not self.POISON_MODE:
            self.update_not_poison_mode_link_down(port)
        else:
            self.update_link_down_poison_mode(port)
        self.port_to_latency.pop(port)

    def update_not_poison_mode_link_down(self, port):
        for host in self.host_to_route.keys():
            if self.host_to_route[host] != None and self.host_to_route[host][1] == port:
                self.host_to_route[host] = None

    def update_link_down_poison_mode(self, port):
        for host in self.host_to_route.keys():
            if self.host_to_route[host] is not None and self.host_to_route[host][1] == port:
                self.poison_state[host] = self.host_to_route[host]
                self.send(basics.RoutePacket(host, INFINITY), flood=True)
                self.host_to_route[host] = None

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())
        if isinstance(packet, basics.RoutePacket):
            if packet.latency + self.port_to_latency[port] < INFINITY:
                self.valid_packet(packet, port)
            elif packet.latency >= INFINITY and self.POISON_MODE:
                for host in self.host_to_route.keys():
                    if host == packet.destination:
                        if self.host_to_route[host] is not None and self.host_to_route[host][1] == port:
                            poison = basics.RoutePacket(packet.destination, INFINITY)
                            self.send(poison, port, flood=True)
                            self.poison_state[host] = self.host_to_route[host]
                            self.host_to_route[host] = None


        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.handle_host_discovery_packet(packet, port)
        else:
            # Totally wrong behavior for the sake of demonstration only: send
            # the packet back to where it came from!
            self.handle_ping(packet, port)
    
    def handle_host_discovery_packet(self, packet, port):
            self.host_to_route[packet.src] = [self.port_to_latency[port], port, -1]
            route_packet = basics.RoutePacket(packet.src, self.port_to_latency[port])
            self.send(route_packet, port, flood=True)

    def handle_ping(self, packet, port):
        if packet.dst in self.host_to_route.keys():
            if self.host_to_route[packet.dst] is not None:
                if self.host_to_route[packet.dst][1] != port:
                    if self.host_to_route[packet.dst][0] <= INFINITY:
                        self.send(packet, self.host_to_route[packet.dst][1], flood=False)

    def valid_packet(self, packet, port):
        new_dist = packet.latency + self.port_to_latency[port];
        if self.POISON_MODE:
            if packet.destination in self.poison_state:
                self.poison_state.pop(packet.destination)
            self.send(basics.RoutePacket(packet.destination, INFINITY), port)
        if packet.destination not in self.host_to_route.keys() \
                or self.host_to_route[packet.destination] is None \
                or self.host_to_route[packet.destination][0] > new_dist:
            self.host_to_route[packet.destination] = \
                [self.port_to_latency[port] + packet.latency, port, api.current_time()]
            self.send(basics.RoutePacket(packet.destination, new_dist), port,
                      flood=True)
        else:
            if new_dist == self.host_to_route[packet.destination][0]:
                if self.host_to_route[packet.destination][2] < api.current_time():
                    self.host_to_route[packet.destination] = \
                        [new_dist, port, api.current_time()]
                    self.send(basics.RoutePacket(
                        packet.destination, new_dist), port, flood=True)
            if self.host_to_route[packet.destination][1] == port:  # ???
                if new_dist > self.host_to_route[packet.destination][0]:
                    self.host_to_route[packet.destination][0] = new_dist
                    self.send(basics.RoutePacket(
                        packet.destination, new_dist), port, flood=True)
                self.host_to_route[packet.destination][2] = api.current_time()
    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        if self.POISON_MODE:
            for p in self.poison_state:
                self.send(basics.RoutePacket(p, INFINITY), flood=True)
        for host in self.host_to_route.keys():
            if self.host_to_route[host] is not None:
                route_has_not_expired = api.current_time() - self.host_to_route[host][2] <= self.ROUTE_TIMEOUT
                host_route = False
                if self.host_to_route[host][2] == -1:
                    host_route = True
                if route_has_not_expired or host_route:
                    self.update_neighbor(host)
                else:
                    self.expired_routes_update(host)

    def update_neighbor(self, host):
        if self.POISON_MODE:
            self.send(basics.RoutePacket(host, INFINITY), self.host_to_route[host][1])
        self.send(basics.RoutePacket(host, self.host_to_route[host][0]), self.host_to_route[host][1], flood=True)

    def expired_routes_update(self, host):
        if self.POISON_MODE:
            self.send(basics.RoutePacket(host, INFINITY), self.host_to_route[host][1])
            self.poison_state[host] = self.host_to_route[host]
        self.host_to_route[host] = None