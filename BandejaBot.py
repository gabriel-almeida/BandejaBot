from pprint import pprint
import sys
import time
import telepot
import Cardapio
import logging
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

__author__ = 'gabriel'
LOG_BOT = 'bandejaBot.log'

class YourBot(telepot.Bot):
    logging.basicConfig(filename=LOG_BOT, level=logging.INFO,
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    def __init__(self, *args, **kwargs):
        super(YourBot, self).__init__(*args, **kwargs)
        self._answerer = telepot.helper.Answerer(self)
        self.cardapio = Cardapio.Cardapio()
        self.cardapio.carrega_cardapio()

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if 'almo' in msg['text'].lower():
            response = self.cardapio.almoco_hoje()
        elif 'janta' in msg['text'].lower():
            response = self.cardapio.janta_hoje()
        else:
            response = self.cardapio.cardapio_mais_proximo()

        bot.sendMessage(chat_id, response, parse_mode='html')
        print('Chat Message:', content_type, chat_type, msg['from']['first_name'] + " " + msg['from']['last_name'])
        logging.info(msg)



if __name__ == '__main__':
    TOKEN = sys.argv[1]  # get token from command-line

    bot = YourBot(TOKEN)
    bot.message_loop()
    print('Listening ...')

    while 1:
        time.sleep(10)