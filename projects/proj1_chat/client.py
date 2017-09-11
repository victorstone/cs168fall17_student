import sys
import socket
import select
import utils

def chat_client():
    if (len(sys.argv) < 3):
        print 'Usage : python chat_client.py hostname port'
        sys.exit()

    username = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)

    # connect to remote host
    try:
        s.connect((host, port))
        s.send(username.ljust(200))
    except:
        print utils.CLIENT_WIPE_ME + "\r" + utils.CLIENT_CANNOT_CONNECT.replace("{0}", host).replace("{1}", str(port))
        sys.exit()

    sys.stdout.write('[Me] ');
    sys.stdout.flush()

    while 1:
        socket_list = [sys.stdin, s]

        # Get the list sockets which are readable
        ready_to_read, ready_to_write, in_error = select.select(socket_list, [], [])

        for sock in ready_to_read:
            if sock == s:
                # incoming message from remote server, s
                data = sock.recv(200, socket.MSG_WAITALL)
                if not data:
                    print utils.CLIENT_WIPE_ME + "\r" + \
                          utils.CLIENT_SERVER_DISCONNECTED.replace("{0}", host).replace("{1}", str(port))
                    sys.exit()
                else:
                    # print data
                    sys.stdout.write(utils.CLIENT_WIPE_ME + "\r" + data.rstrip()+"\n")
                    sys.stdout.write('[Me] ');
                    sys.stdout.flush()

            else:
                # user entered a message
                msg = sys.stdin.readline()
                s.send(msg.ljust(200))
                sys.stdout.write('[Me] ')
                sys.stdout.flush()

chat_client()
