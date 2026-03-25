#from tkinter import *
import tkinter as tk
#from tkinter import scrolledtext
#from spur_search import spur_cal

from new_sinad_1 import SoundCard
# import PySimpleGUI as sg
import matplotlib.pyplot as plt
import numpy as np
import collections


window= tk.Tk()
window.title("GME SINAD Meter")
window.geometry('1000x600')

scale_widget = tk.Scale(window, from_=0.0, to=50.0, digits=3, resolution=0.1,
                        label= "SINAD", orient=tk.HORIZONTAL)
scale_widget.set(25)
scale_widget.grid(row=1,column=1)
#scale_widget.pack()

def my_upd():
    print('Check box value :',ccitt.get())

ccitt=tk.BooleanVar()
c1 = tk.Checkbutton(window, text='CCITT', variable=ccitt,
	onvalue=True,offvalue=False,command=my_upd)
c1.grid(row=2,column=1)


sc = SoundCard()

max_samples = 20  # limit the size of the collection by limiting number of Sinad samples it contains
sinad = collections.deque(
    np.zeros(max_samples))  # create collection with all zeros.'Deque' is  an updated version of list


def my_function():  # this function ensures the Deque size stays at the initialized value
    sinad.popleft()
    sinad.append(value)


while True:  # measure Sinad until break

    #ccitt = True
    print('CCITT filter ON :', ccitt.get())
    #value = sc.measure(num_samps=4096 * 4, ccitt=False)  # get SINAD change to "True" for CCIT weighting
    num_samps= 4096*4
    #b=ccitt.get()
    value = sc.measure(num_samps, ccitt.get())  # get SINAD change to "True" for CCIT weighting
    print('sinad : ', value)
    scale_widget.set(value)
    my_function()  # call Deque trim function
    plt.cla()  # clear axes to update plot
    plt.plot(sinad, 'b--')  # plot SINAD
    plt.scatter(len(sinad) - 1, sinad[-1])

    # Set axes scaling
    if value <= 5:
        plt.ylim(2, 12)  # set plot y-axis limits
    elif value > 5 and value <= 18:
        plt.ylim(4, 20)  # set plot y-axis limits
    # elif value >10 and value <20:
    #   plt.ylim(8,22) # set plot y-axis limits
    else:
        plt.ylim(18, 40)  # set plot y-axis limits

    plt.xlim(0, 20)  # set x-axis limits

    # window decorations
    plt.xlabel("Samples")
    plt.ylabel("SINAD")
    plt.suptitle("SINAD Meter")
    #plt.grid(b=True, which='major', color='#666666', linestyle='--')
    plt.grid(visible=True, which='major', color='#666666', linestyle='--')
    plt.pause(0.05)  # pause to allow plot window to update

plt.show()
