import sys
import Cardapio
import logging
import re
import telegram
import telegram.ext
import os


class BandejaBot:
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

    def __init__(self):
        self.cardapio = Cardapio.Cardapio()
        self.cardapio.carrega_cardapio()

    def start(self):
        if self.cardapio.cardapio is not None:
            ultima_atualizacao = self.cardapio.ultima_atualizacao.strftime(self.FORMATO_DATA_HORA)
            vigencia = self.cardapio.data_inicio_vigencia().strftime(self.FORMATO_DATA)
            response = self.MENSAGEM_START % (ultima_atualizacao, vigencia)
        else:
            response = self.MENSAGEM_START % ("N/A", "N/A")
        return response

    def horarios(self):
        return self.MENSAGEM_HORARIOS

    def destaques(self):
        response = self.cardapio.compoe_destaques()
        return response

    def almoco(self):
        response = self.cardapio.almoco_hoje()
        return response

    def janta(self):
        response = self.cardapio.janta_hoje()
        return response

    def bandeja(self):
        response = self.cardapio.cardapio_mais_proximo()
        return response

    def opcoes_dias_semana(self):
        teclado = [Cardapio.DIAS_DA_SEMANA[0:3], Cardapio.DIAS_DA_SEMANA[3:]]
        response = "Qual dia?"
        return response, teclado

    def opcoes_refeicao(self, dia_semana):
        teclado = [[Cardapio.ORDEM_REFEICAO[0] + " de " + dia_semana,
                    Cardapio.ORDEM_REFEICAO[1] + " de " + dia_semana]]
        response = "Qual refeição?"
        return response, teclado

    def cardapio_semana(self, refeicao, dia_semana):
        response = self.cardapio.get_cardapio(refeicao=refeicao, dia=dia_semana)
        return response


class TelegramBot:
    REGEXP_CARDAPIO_SEMANA = re.compile('(%s) de (%s)' %
                                        ("|".join(Cardapio.ORDEM_REFEICAO), "|".join(Cardapio.DIAS_DA_SEMANA)))
    REGEXP_DIAS_SEMANA = re.compile('(%s)' % "|".join(Cardapio.DIAS_DA_SEMANA))
    MENSAGEM_ERRO = "Um erro ocorreu."

    def __init__(self, log_file, id_mestre):
        self.id_mestre = id_mestre
        self.log_file = log_file

    @staticmethod
    def envio_mensagem_padrao(bot, update, resposta, teclado=None):
        """
        Padrao de envio de respostas deste bot
        """
        bot.sendMessage(update.message.chat_id, reply_markup=teclado,
                        text=resposta, disable_web_page_preview=True, parse_mode="html")

    @staticmethod
    def callback_resposta_direta(texto_resposta):
        """
        Retorna uma funcao lambda que será usada como callback para um hadler.
        Em especial, este callback apenas responderá o usuario com um texto fixo
        """
        return lambda bot, update: TelegramBot.envio_mensagem_padrao(bot, update, resposta=texto_resposta)

    @staticmethod
    def callback_log_wrapper(callback):
        """
        Envelopa uma função de callback de forma a sempre realizar
        um logging da mensagem recebida antes de chamar o callback
        """
        def _wrapper(update, bot):
            logging.info(str(update))
            callback(update, bot)
        return _wrapper

    @staticmethod
    def callback_erro(bot, update, error):
        logging.info(str(error))
        TelegramBot.envio_mensagem_padrao(bot, update, TelegramBot.MENSAGEM_ERRO)

    @staticmethod
    def cria_handler(comando_ou_regexp, callback_ou_mensagem):
        """
        Funcao Utilitária para se criar handlers específicos com o tipo de entrada
        :param comando_ou_regexp: String de um comando ou regexp que será pareada
        :param callback_ou_mensagem: funcao de callback ou texto fixo da mensagem
        :return: Handler construido
        """
        if callable(callback_ou_mensagem):
            callback = callback_ou_mensagem
        else:
            callback = TelegramBot.callback_resposta_direta(callback_ou_mensagem)

        callback = TelegramBot.callback_log_wrapper(callback)

        if type(comando_ou_regexp) is str:
            comando = comando_ou_regexp
            return telegram.ext.CommandHandler(comando, callback)
        else:
            regexp = comando_ou_regexp
            return telegram.ext.RegexHandler(regexp, callback)

    def callback_cardapio_lista_semana(self, bot, update):
        texto_resposta, lista_teclado = self.bandeja.opcoes_dias_semana()
        teclado = telegram.ReplyKeyboardMarkup(lista_teclado, one_time_keyboard=True)
        TelegramBot.envio_mensagem_padrao(bot, update, texto_resposta, teclado)

    def callback_cardapio_lista_refeicao(self, bot, update):
        dia_semana = update.message.text
        texto_resposta, lista_teclado = self.bandeja.opcoes_refeicao(dia_semana)
        teclado = telegram.ReplyKeyboardMarkup(lista_teclado, one_time_keyboard=True)
        TelegramBot.envio_mensagem_padrao(bot, update, texto_resposta, teclado)

    def callback_cardapio_dia_especifico(self, bot, update):
        cardapio_desejado = update.message.text
        resultado = cardapio_desejado.split(' de ')
        texto_resposta = self.bandeja.cardapio_semana(resultado[0], resultado[1])
        TelegramBot.envio_mensagem_padrao(bot, update, texto_resposta)

    def manda_log(self, bot, job):
        bot.sendMessage(self.id_mestre, text="INICIADO",
                        disable_web_page_preview=True, parse_mode="html")

    def inicia_bot(self, token, ip, port, webhook_url):
        updater = telegram.ext.Updater(token)
        self.bandeja = BandejaBot()

        updater.dispatcher.add_handler(TelegramBot.cria_handler('start', self.bandeja.start()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('start', self.bandeja.start()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('horarios', self.bandeja.horarios()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('destaque', self.bandeja.destaques()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('almoco', self.bandeja.almoco()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('janta', self.bandeja.janta()))
        updater.dispatcher.add_handler(TelegramBot.cria_handler('bandeja', self.bandeja.bandeja()))

        # Teclado com dias da semana
        updater.dispatcher.add_handler(TelegramBot.cria_handler('semana',
                                                                   self.callback_cardapio_lista_semana))
        updater.dispatcher.add_handler(TelegramBot.cria_handler(self.REGEXP_DIAS_SEMANA,
                                                                 self.callback_cardapio_lista_refeicao))
        updater.dispatcher.add_handler(TelegramBot.cria_handler(TelegramBot.REGEXP_CARDAPIO_SEMANA,
                                                                 self.callback_cardapio_dia_especifico))

        updater.dispatcher.add_error_handler(TelegramBot.callback_erro)

        jobs = updater.job_queue
        # jobs.put(telegram.ext.Job(self.manda_log, 60, repeat=True))

        updater.start_webhook(port=port, url_path=TOKEN)
        # updater.bot.setWebhook(webhook_url + "/" + TOKEN)

        logging.info("Bot Iniciado", "Porta:", port,
                     "URL:", webhook_url)
        logging.info(str(updater.bot.get_me()))
        # self.manda_log(updater.bot, None)
        updater.idle()


if __name__ == '__main__':
    TOKEN = sys.argv[1]
    ID_MESTRE = sys.argv[2]
    PORT = int(sys.argv[3])
    APP_NAME = "bandejabot"
    URL = "https://%s.herokuapp.com" % APP_NAME
    IP = "127.0.0.1"
    LOG_BOT = 'bandeja_bot.log'

    logging.basicConfig(level=logging.INFO, format='%(asctime)s\t%(levelname)s\t%(message)s')

    bot = TelegramBot(LOG_BOT, ID_MESTRE)
    bot.inicia_bot(TOKEN, IP, PORT, APP_NAME)
