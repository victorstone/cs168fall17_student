import sys
import socket
import select
import utils

SOCKET_LIST = []
RECV_BUFFER = 200
ARGS = sys.argv
HOST = ''


# List of valid commands
COMMANDS = {'/create', '/join', '/list'}

def is_valid_command(message):
    message = message.rstrip("\n ")
    command_with_args = message.split(" ", 1)
    command = command_with_args[0]
    if message.startswith("/"):
        if command in COMMANDS:
            if command == '/create' or command == '/join':
                return command, command_with_args[1]
            else:
                return command, ""
    return command, ""

def chat_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    socket_username_map = {}
    # Channel name to list of sockfds, so that broadcast can only send to those people.
    channel_sockets_map = {}
    socket_channel_map = {}

    # add server socket object to the list of readable connections
    SOCKET_LIST.append(server_socket)

    print "Chat server started on port " + str(PORT)

    while 1:

        # get the list sockets which are ready to be read through select
        # 4th arg, time_out  = 0 : poll and never block
        ready_to_read, ready_to_write, in_error = select.select(SOCKET_LIST, [], [], 0)

        for sock in ready_to_read:
            # a new connection request recieved
            if sock == server_socket:
                sockfd, addr = server_socket.accept()
                SOCKET_LIST.append(sockfd)

            # a message from a client, not a new connection
            else:
                # process data recieved from client,
                try:
                    # receiving data from the socket.
                    data = sock.recv(RECV_BUFFER, socket.MSG_WAITALL)
                    if data:
                        if sock not in socket_username_map:
                            username = data.rstrip()
                            socket_username_map[sock] = username
                            print "User " + username.rstrip(" ") + " has connected at port " + str(addr)
                        else:
                            # there is something in the socket
                            possible_command, possible_arguments = is_valid_command(data)
                            if possible_command in COMMANDS:
                                if possible_command == "/list":
                                    channels = utils.CLIENT_WIPE_ME + "\r"
                                    for key in channel_sockets_map:
                                        channels += key + "\n"
                                    sock.send(channels.ljust(200))
                                elif possible_command == "/create":
                                    if possible_arguments == "":
                                        sock.send((utils.CLIENT_WIPE_ME + "\r" + utils.SERVER_CREATE_REQUIRES_ARGUMENT + "\n").ljust(200))
                                    elif possible_arguments in channel_sockets_map:
                                        sock.send((utils.CLIENT_WIPE_ME + "\r" + utils.SERVER_CHANNEL_EXISTS.replace("{0}",
                                                  possible_arguments) + "\n").ljust(200))
                                    else:
                                        if sock in socket_channel_map:
                                            broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                                                      utils.SERVER_CLIENT_LEFT_CHANNEL
                                                      .replace("{0}", socket_username_map[sock])
                                                      + "\n", socket_list=channel_sockets_map[socket_channel_map[sock]])
                                            channel_sockets_map[socket_channel_map[sock]].remove(sock)
                                        channel_sockets_map[possible_arguments] = {sock}
                                        socket_channel_map[sock] = possible_arguments
                                # it's gotta be /join
                                elif possible_command == "/list":
                                    if possible_arguments == "":
                                        sock.send((utils.CLIENT_WIPE_ME + "\r" + utils.SERVER_JOIN_REQUIRES_ARGUMENT + "\n".ljust(200)))
                                    elif possible_arguments not in channel_sockets_map:
                                        sock.send((utils.CLIENT_WIPE_ME + "\r" + utils.SERVER_NO_CHANNEL_EXISTS.replace("{0}",
                                                  possible_arguments) + "\n".ljust(200)))
                                    elif sock in channel_sockets_map[possible_arguments]:
                                        sock.send((utils.CLIENT_WIPE_ME + "\r" + "lol" 
                                                  + "\n".ljust(200)))
                                    else:
                                        print "User " + socket_username_map[sock] + " is joining"
                                        if sock in socket_channel_map:
                                            broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                                                      utils.SERVER_CLIENT_LEFT_CHANNEL
                                                      .replace("{0}", possible_arguments) + "\n",
                                                      channel_sockets_map[socket_channel_map[sock]])
                                            channel_sockets_map[socket_channel_map[sock]].remove(sock)
                                        channel_sockets_map[possible_arguments].add(sock)
                                        socket_channel_map[sock] = possible_arguments
                                        broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                                                  utils.SERVER_CLIENT_JOINED_CHANNEL
                                                  .replace("{0}", socket_username_map[sock]) + "\n",
                                                  socket_list=channel_sockets_map[possible_arguments])
                            else:
                                if sock not in socket_channel_map:
                                    sock.send((utils.CLIENT_WIPE_ME + "\r" + utils.SERVER_CLIENT_NOT_IN_CHANNEL + "\n".ljust(200)))
                                else :
                                    broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                                              '[' + socket_username_map[sock] + '] ' + data.rstrip(" "),
                                              socket_list=channel_sockets_map[socket_channel_map[sock]])
                    else:
                        # remove the socket that's broken
                        broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                                  utils.SERVER_CLIENT_LEFT_CHANNEL
                                  .replace("{0}", socket_username_map[sock])
                                  + "\n", socket_list=channel_sockets_map[socket_channel_map[sock]])
                        channel_sockets_map[socket_channel_map[sock]].remove(sock)
                        if sock in SOCKET_LIST:
                            SOCKET_LIST.remove(sock)
                        if sock in socket_channel_map:
                            if sock in channel_sockets_map[socket_channel_map[sock]]:
                                channel_sockets_map[socket_channel_map[sock]].remove(sock)
                            del socket_channel_map[sock]

                        # at this stage, no data means probably the connection has been broken
                        del socket_username_map[sock]

                        # exception
                except Exception as e:
                    print e.message
                    broadcast(server_socket, sock, utils.CLIENT_WIPE_ME + "\r" +
                              utils.SERVER_CLIENT_LEFT_CHANNEL
                              .replace("{0}", socket_username_map[sock])
                              + "\n", socket_list=channel_sockets_map[socket_channel_map[sock]])
                    channel_sockets_map[socket_channel_map[sock]].remove(sock)
                    if sock in SOCKET_LIST:
                        SOCKET_LIST.remove(sock)
                    if sock in socket_channel_map:
                        if sock in channel_sockets_map[socket_channel_map[sock]]:
                            channel_sockets_map[socket_channel_map[sock]].remove(sock)
                        del socket_channel_map[sock]
                    del socket_username_map[sock]
                    continue

    server_socket.close()


# broadcast chat messages to all connected clients
def broadcast(server_socket, sock, message, socket_list=SOCKET_LIST):
    for socket in socket_list:
        # send the message only to peer
        if socket != server_socket and socket != sock:
            try:
                socket.send(message.ljust(200))
            except:
                # broken socket connection
                socket.close()
                # broken socket, remove it
                if socket in SOCKET_LIST:
                    SOCKET_LIST.remove(socket)



if len(ARGS) != 2:
    print "Please supply a port."
    sys.exit()
PORT = int(ARGS[1])
chat_server()
