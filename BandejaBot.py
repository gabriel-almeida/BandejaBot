from pprint import pprint
import sys
import time
import telepot
import Cardapio
import logging
import unicodedata
import re

from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton

__author__ = 'gabriel'
LOG_BOT = 'bandejaBot.log'
MENSAGEM_START = """
        Para obter o cardápio, use os comandos fornecidos ou simplesmente diga a palavras-chave abaixo:
        <b>/almoco</b> e <b>/janta</b>: Retorna o cardápio do dia para o almoço e janta, respectivamente;
        <b>/bandeja</b>: Será respondido o cardápio da próxima refeição (apartir de 14h é considerado jantar);
        <b>/semana</b>: Cardápio da um dia arbitrário da semana, que o bot irá perguntar, para uma resposta direta,\
        use comandos como <i>Almoço de Segunda</i>;
        <b>/horarios</b>: Horários de funcionamento dos diversos restaurantes;
        <b>/help</b>: Exibe este diálogo.
        Última atualização efetiva: %s
        Inicio da vigência do cardápio atual: %s
        Código-fonte disponível <a href="github.com/gabriel-almeida/BandejaBot">aqui</a>.
        """

MENSAGEM_HORARIOS = """
        <i>De Segunda a Sexta</i>:
        <b>Central</b>:
            <i>Almoço</i>: 11h-14h
            <i>Jantar</i>: 17:30h-20:00h
        <b>CT</b>:
            <i>Almoço</i>: 10:30h-14:30h
            <i>Jantar</i>: 17:30h-20:00h
        <b>Letras</b>:
            <i>Almoço</i>: 11:15h-14:00h
            <i>Jantar</i>: 17:30h-20:00h

        <i>Fim de semana e Feriados</i> (Somente <b>Central</b>):
            <i>Almoço</i>: 12:00h-14:00h
            <i>Jantar</i>: 17:00h-19:15h
        """

FORMATO_DATA_HORA = "%d/%m/%Y %H:%M:%S"
FORMATO_DATA = "%d/%m/%Y"

REGEXP_CARACTERES_ACEITAVEIS = re.compile('[^a-z0-9 ]')
REGEXP_ESPACOS = re.compile('[ ]+')
REGEXP_CARDAPIO_SEMANA = re.compile('(%s) de (%s)' %
                                    ("|".join(Cardapio.ORDEM_REFEICAO), "|".join(Cardapio.DIAS_DA_SEMANA)))



class YourBot(telepot.Bot):
    def __init__(self, *args, **kwargs):
        self.cardapio = Cardapio.Cardapio()
        self.cardapio.carrega_cardapio()
        super(YourBot, self).__init__(*args, **kwargs)

    #par sensor-atuador

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if 'text' in msg:
            txt = msg['text'].lower()
            reply_markup = None
            if '/start' in txt or '/help' in txt:
                if self.cardapio.cardapio is not None:
                    ultima_atualizacao = self.cardapio.ultima_atualizacao.strftime(FORMATO_DATA_HORA)
                    vigencia = self.cardapio.data_inicio_vigencia().strftime(FORMATO_DATA)
                    response = MENSAGEM_START % (ultima_atualizacao, vigencia)
                else:
                    response = MENSAGEM_START % ("N/A", "N/A")
            elif '/horarios' in txt:
                response = MENSAGEM_HORARIOS
            elif '/destaque' in txt:
                response = self.cardapio.compoe_destaques()
            elif '/semana' in txt:
                reply_markup = {'keyboard': [Cardapio.DIAS_DA_SEMANA[0:3], Cardapio.DIAS_DA_SEMANA[3:]]}
                response = "Qual dia?"
            elif txt in Cardapio.DIAS_DA_SEMANA:
                reply_markup = {'keyboard': [[Cardapio.ORDEM_REFEICAO[0] + " de " + txt,
                                              Cardapio.ORDEM_REFEICAO[1] + " de " + txt]]}
                response = "Qual refeição?"

            elif REGEXP_CARDAPIO_SEMANA.match(txt):
                reply_markup = {'hide_keyboard': True}
                resultado = txt.split(' de ')
                response = self.cardapio.get_cardapio(resultado[0], resultado[1])
            elif 'almo' in txt:
                response = self.cardapio.almoco_hoje()
            elif 'janta' in txt:
                response = self.cardapio.janta_hoje()
            elif 'bandeja' in txt:
                response = self.cardapio.cardapio_mais_proximo()
            else:
                logging.info(msg)
                return

            bot.sendMessage(chat_id, response, parse_mode='html', reply_markup=reply_markup,
                            disable_web_page_preview=True)

        logging.info(msg)

        try:
            remetente = msg['from']['first_name'] + " " + msg['from']['last_name']
        except:
            remetente = chat_id

        print('Chat Message:', content_type, chat_type, remetente)

    def on_inline_query(self, msg):
        pass

    def on_chosen_inline_result(self, msg):
        pass


if __name__ == '__main__':
    TOKEN = sys.argv[1]  # get token from command-line

    # Tento a todo custo inicializar o bot
    # TODO NAO FUNCIONA
    while True:
        try:
            bot = YourBot(TOKEN)
            bot.message_loop()
            print('Inicializado...')
            break
        except:
            print("Erro ao inicializar, tentando novamente...")
            time.sleep(5)

    while 1:
        time.sleep(10)