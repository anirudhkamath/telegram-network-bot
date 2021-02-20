import re

from napalm.base import get_network_driver
from netmiko.ssh_autodetect import SSHDetect
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, ConversationHandler, CallbackContext

# Mapping the netmiko type that is returned by SSH autodetect functionality by netmiko
NETMIKO_OS_TO_DRIVER_MAP = {
    "cisco_ios": "ios",
    "cisco_nxos": "nxos_ssh"
}

CHOOSE, CHOICE, DONE = range(3) # Three numbered states the chatbot resides at after communication has started.

def get_device_facts(ip_addr):
    """ Method to get facts about the device """
    remote_device = {
        "device_type": "autodetect",
        "host": ip_addr,
        "username": "<<< YOUR REMOTE LOGIN USERNAME >>>",
        "password": "<<< YOUR REMOTE LOGIN PASSWORD >>>",
    }
    guesser = SSHDetect(**remote_device)
    netmiko_guessed_os = guesser.autodetect()

    # get NAPALM driver name from MAPPER dict created above
    print(f"{ip_addr}: GET NAPALM DRIVER NAME FROM NETMIKO GUESSED OS PLATFORM")
    driver_name = NETMIKO_OS_TO_DRIVER_MAP.get(netmiko_guessed_os, None)
    if not driver_name:
        print(f"{ip_addr}: NETMIKO GUESSED OS PLATFORM DOES NOT MAP TO A NAPALM DRIVER")
        # if the OS type does not exist in the mapper dict, which means driver_name is None
        return None

    print(f"{ip_addr}: USING NAPALM DRIVER TO CONNECT TO THE DEVICE")
    driver = get_network_driver(driver_name)
    device = driver(
        ip_addr, "<<< YOUR REMOTE LOGIN USERNAME >>>", "<<< YOUR REMOTE LOGIN PASSWORD >>>"
    )
    device.open()

    res = device.get_facts()

    return res

def get_device_interfaces(ip_addr):
    """ Method to get interfaces of the device  """
    remote_device = {
        "device_type": "autodetect",
        "host": ip_addr,
        "username": "<<< YOUR REMOTE LOGIN USERNAME >>>",
        "password": "<<< YOUR REMOTE LOGIN PASSWORD >>>",
    }
    guesser = SSHDetect(**remote_device)
    netmiko_guessed_os = guesser.autodetect()

    # get NAPALM driver name from MAPPER dict created above
    print(f"{ip_addr}: GET NAPALM DRIVER NAME FROM NETMIKO GUESSED OS PLATFORM")
    driver_name = NETMIKO_OS_TO_DRIVER_MAP.get(netmiko_guessed_os, None)
    if not driver_name:
        print(f"{ip_addr}: NETMIKO GUESSED OS PLATFORM DOES NOT MAP TO A NAPALM DRIVER")
        # if the OS type does not exist in the mapper dict, which means driver_name is None
        return None

    print(f"{ip_addr}: USING NAPALM DRIVER TO CONNECT TO THE DEVICE")
    driver = get_network_driver(driver_name)
    device = driver(
        ip_addr, "<<< YOUR REMOTE LOGIN USERNAME >>>", "<<< YOUR REMOTE LOGIN PASSWORD >>>"
    )
    device.open()

    res = device.get_interfaces()

    return res

def start(update: Update, context: CallbackContext) -> int:
    """ The start to the conversation """
    update.message.reply_text(
        'Hello, I am your network bot. You can talk to me to get information about devices in your network.\n\n'
        'Send me a "Done" if you want to stop this interaction at any time\n\n'
        'Please tell me the primary IP address of the device you want to get information about.',
    )

    return CHOOSE

def choose_option(update: Update, context: CallbackContext) -> int:
    """ Choose what you want bot to get you from the device """
    reply_keyboard = [['Facts', 'Interfaces']]
    context.user_data['ipaddr'] = update.message.text
    update.message.reply_text(
        'Awesome, what do you want to get for this device?',
        reply_markup= ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return CHOICE

def choice_wrapper(update: Update, context: CallbackContext) -> int:
    """ Wrapper around method calls that get information for the bot to send back """
    text = update.message.text
    ip_addr = context.user_data['ipaddr']
    if text == 'Facts':
        update.message.reply_text("Please wait while I get general facts about your device...")
        device_facts = get_device_facts(ip_addr)

        if not device_facts:
            update.message.reply_text("Sorry, this device type is not supported yet.")

        else:
            update.message.reply_text(
                'Here are your device facts:\n\n'
                f'This device\'s name is {str(device_facts["hostname"])}, serial number {str(device_facts["serial_number"])}\n'
                f'It is a {str(device_facts["vendor"])} {str(device_facts["model"])}, running {str(device_facts["os_version"])} \n'
                f'This device has been up for {str(device_facts["uptime"])}\n\n'
                f'The list of interfaces on this device:\n\n {str(device_facts["interface_list"])}'
            )

    if text == 'Interfaces':
        update.message.reply_text("Please wait while I get information about working interfaces on your device...")
        device_interfaces = get_device_interfaces(ip_addr)

        if not device_interfaces:
            update.message.reply_text("Sorry, this device type is not supported yet.")

        else:
            update.message.reply_text('Here are facts about your device interfaces:\n\n')
            
            for d in device_interfaces:
                if device_interfaces[d]['is_up'] and device_interfaces[d]['is_enabled']:
                    update.message.reply_text(
                        f'About interface {str(d)}:\n\n'
                        f'It has a burnt in address of {device_interfaces[d]["mac_address"]}'
                        f'And supports a speed of {device_interfaces[d]["speed"]} Mbps, with an MTU of {device_interfaces[d]["mtu"]}'
                    )

    return DONE

def done(update: Update, context: CallbackContext) -> int:
    """ Conversation end """
    user_data = context.user_data
    if 'ipaddr' in user_data:
        del user_data['ipaddr']

    update.message.reply_text(
        f"Closing the connection to the device. Ciao!"
    )

    user_data.clear()
    return ConversationHandler.END


def main():
    """ Main method that defines what the server is running """
    print("STARTING BOT SET UP")
    updater = Updater("<<< YOUR BOT TOKEN FROM TELEGRAM BOTFATHER >>>", use_context=True) # provides the interface to the bot
    dispatcher = updater.dispatcher
    print("STARTING CONVERSATION HANDLER")
    convo_handler = ConversationHandler(
        entry_points= [CommandHandler('start', start)],
        states= {
            CHOOSE: [MessageHandler(Filters.regex("^(\d{1,3}\.){3}\d{1,3}$"), choose_option)],
            CHOICE: [MessageHandler(Filters.regex('^(Facts|Interfaces)$'), choice_wrapper)],
            DONE: [MessageHandler(Filters.regex('^[dD]one$'), done)]
        },
        fallbacks=[MessageHandler(Filters.regex('^[dD]one$'), done)],
    )
    print("DISPATCHING HANDLER")
    dispatcher.add_handler(convo_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()