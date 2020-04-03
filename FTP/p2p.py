import tkinter as tk  # python 3
from tkinter import font as tkfont  # python 3
from tkinter import messagebox
import socket
import time
import threading
import emoji
import re
import struct
import sys


class SampleApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        listening_thread = threading.Thread(target=self.listen_for_connections)
        listening_thread.start()
        self.socket_connection = None
        self.address = None
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartPage, ChatPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def on_closing(self):
        if tk.messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.quit_cmd()
            self.destroy()

    # Function that sends a closing notification to server and closes connection
    def quit_cmd(self):
        print('Closing connection with server')
        self.send_msg(b'CLOSE_CONNECTION')  # Sending closing message to server
        time.sleep(1)
        if self.socket_connection is not None:
            self.socket_connection.close()  # Closing on clients end
        print('Exiting')
        self.destroy()
        sys.exit()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def listen_for_connections(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # creating socket for server
        server_socket.bind(('', 0))
        server_socket.listen()
        print('The server is listening on', (socket.gethostbyname(socket.gethostname()),
                                             server_socket.getsockname()[1]))
        while self.socket_connection is None:
            try:
                self.socket_connection, self.address = server_socket.accept()  # listening for client connection requests
                print('Accepted connection from', self.address)
            except KeyboardInterrupt:
                break
        self.accept_connection(self.socket_connection)

    def accept_connection(self, socket_connection):
        self.socket_connection = socket_connection
        self.show_frame("ChatPage")
        listening_thread = threading.Thread(target=self.listen_for_messages)
        listening_thread.start()


    def listen_for_messages(self):
        print("listening for messages")
        while True:
            received_data = self.receive_message(self.socket_connection)
            if received_data == b'CLOSE_CONNECTION':
                print('Closing connection')
                if self.socket_connection is not None:# closing connection with client
                    self.socket_connection.close()
                self.destroy()
                sys.exit()
            else:
                self.frames["ChatPage"].show_frieds_new_message(received_data.decode())

    # Function to receive message from the socket
    def receive_message(self, sock):
        # Read message length and unpack it into an integer
        raw_msglen = self.receive_all(sock, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Read the message data
        return self.receive_all(sock, msglen)

    # Helper function to receive_message for n bytes or return None if EOF is hit
    def receive_all(self, sock, n):
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    # Function to send messages to server
    def send_msg(self, msg):
        # Prefix each message with a 4-byte length (network byte order)
        msg = struct.pack('>I', len(msg)) + msg
        self.socket_connection.sendall(msg)


class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Welcome to my chat application.\nEmojis are enabled so check it out!",
                         font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        ip_label = tk.Label(self, text="Enter ip address")
        port_label = tk.Label(self, text="Enter port number")
        ip_entry = tk.Entry(self)
        port_entry = tk.Entry(self)
        connect_button = tk.Button(self, text="Connect",
                                   command=lambda: self.try_to_connect(ip_entry.get(), port_entry.get()))
        ip_label.pack()
        ip_entry.pack()
        port_label.pack()
        port_entry.pack()
        connect_button.pack()

    def try_to_connect(self, ip, port):
        if not is_int(port) and 0 <= int(port) <= 65535:  # checks to see if it's a valid port
            print("Port number must be a valid integer from 0 to 65535: ", port)
            return None
        new_socket = None
        try:  # creates socket to communicate with server
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect((ip, int(port)))
            time.sleep(1)
            self.controller.accept_connection(new_socket)

            print("Connection to", (ip, port), "was made successfully")
        except Exception:  # if connection is unsuccessful
            print("Connection to", (ip, port), "was unsuccessful")


class ChatPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self._nonbmp = re.compile(r'[\U00010000-\U0010FFFF]')
        self.controller = controller
        text_area = tk.Frame()
        text_area.pack(side=tk.TOP)

        label_you = tk.Label(text_area, text="Your messages")
        label_you.pack(side=tk.RIGHT)

        self.user_messages = tk.Text(text_area)
        self.user_messages.pack(side=tk.RIGHT)

        label_them = tk.Label(text_area, text="Guest messages")
        label_them.pack(side=tk.LEFT)

        self.friend_messages = tk.Text(text_area)
        self.friend_messages.pack(side=tk.LEFT)

        self.input_user = tk.StringVar()
        self.input_field = tk.Entry(text=self.input_user)
        self.input_field.pack(side=tk.BOTTOM, fill=tk.X)

        frame = tk.Frame()
        self.input_field.bind("<Return>", self.enter_pressed)
        frame.pack()

    def enter_pressed(self, event):
        input_get = self.input_field.get()
        emojiboy = emoji.emojize(input_get)
        self.user_messages.insert(tk.INSERT, '%s\n' % self.with_surrogates(emoji.emojize(input_get, use_aliases=True)))
        self.input_user.set('')
        self.send_message(emojiboy)
        return "break"

    def show_frieds_new_message(self, msg):
        self.friend_messages.insert(tk.INSERT, '%s\n' % self.with_surrogates(emoji.emojize(msg, use_aliases=True)))

    def _surrogatepair(self, match):
        char = match.group()
        assert ord(char) > 0xffff
        encoded = char.encode('utf-16-le')
        return (
                chr(int.from_bytes(encoded[:2], 'little')) +
                chr(int.from_bytes(encoded[2:], 'little')))

    def with_surrogates(self, text):
        return self._nonbmp.sub(self._surrogatepair, text)

    def send_message(self, msg):
        self.controller.send_msg(msg.encode())

# Helper function to check if value is an integer
def is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    app = SampleApp()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
