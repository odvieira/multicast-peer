import asyncio
import multiprocessing
from random import randint
import tkinter

from MulticastPeer import MulticastPeer

peer_pipe_rcv, peer_pipe_snd = multiprocessing.Pipe(duplex=False)
state_rcv, state_snd = multiprocessing.Pipe(duplex=False)


def send_command_join() -> None:
    peer_pipe_snd.send('JOIN')


def send_command_acquire_lock() -> None:
    peer_pipe_snd.send('ALOCK')


def send_command_release_lock() -> None:
    peer_pipe_snd.send('RLOCK')


def send_command_exit() -> None:
    peer_pipe_snd.send('EXIT')


async def run_tk(root, interval=0.1, label_state: tkinter.Label = None) -> None:
    try:
        while True:
            if state_rcv.poll():
                try:
                    new_state = state_rcv.recv()
                except EOFError:
                    return
                except:
                    raise

                label_state.config(text=new_state)

            root.update()
            await asyncio.sleep(interval)
    except:
        send_command_exit()
    finally:
        return


async def main():
    peer = MulticastPeer(id=randint(
        11, 99), pipe_command=peer_pipe_rcv, pipe_state_snd=state_snd)

    root_obj = tkinter.Tk()

    root_obj.title('Multicast Peer')

    root_obj.geometry("320x320")
    root_obj.resizable(False, False)

    button_join = tkinter.Button(
        root_obj, width=25, activebackground='gold', text="Join Group", command=send_command_join)
    button_join.pack(side='top', expand=1)

    button_request = tkinter.Button(
        root_obj, width=25, activebackground='gold', text="Acquire Lock", command=send_command_acquire_lock)
    button_request.pack(side='top', expand=1)

    button_request = tkinter.Button(
        root_obj, width=25, activebackground='gold', text="Release Lock", command=send_command_release_lock)
    button_request.pack(side='top', expand=1)

    button_exit = tkinter.Button(
        root_obj, width=25, activebackground='gold', text="Close Connection", command=send_command_exit)
    button_exit.pack(side='top', expand=1)

    label_state = tkinter.Label(root_obj, bg='black', \
        fg='green', width=80, justify='center', pady=8, font=("Noto mono", 12))
    label_state.pack(side='top')

    await asyncio.gather(
        peer.listen(),
        peer.active(),
        run_tk(root_obj, 0.1, label_state)
    )

if __name__ == '__main__':
    asyncio.run(main())
