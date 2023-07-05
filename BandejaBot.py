import functools
import Cardapio
import logging
import re
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, StringRegexHandler, filters


class BandejaBot:
    MENSAGEM_START = """
            Para obter o cardápio, use os comandos fornecidos ou simplesmente diga a palavras-chave abaixo:
            <b>/almoco</b> e <b>/janta</b>: Retorna o cardápio do dia para o almoço e janta, respectivamente;
            <b>/bandeja</b>: Será respondido o cardápio da próxima refeição (apartir de 14h é considerado jantar);
            <b>/semana</b>: Cardápio da um dia arbitrário da semana, que o bot irá perguntar. Para uma resposta direta,\
            use comandos como <i>almoço de segunda</i>;
            <b>/horarios</b>: Horários de funcionamento dos diversos restaurantes;
            <b>/help</b>: Exibe este diálogo.
            Última atualização efetiva: %s
            Inicio da vigência do cardápio atual: %s
            Código-fonte disponível <a href="github.com/gabriel-almeida/BandejaBot">aqui</a>.
            """

    MENSAGEM_HORARIOS = """<i>De Segunda a Sexta</i>:
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


def log_request(fn):
    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        try:
            logging.info(args[1].to_json())
            return fn(*args, **kwargs)
        except Exception as ex:
            logging.error("Exception {0}".format(ex))
            raise ex
    return decorated

class TelegramBot:
    REGEXP_CARDAPIO_SEMANA = re.compile('(%s) de (%s)' %
                                        ("|".join(Cardapio.ORDEM_REFEICAO), "|".join(Cardapio.DIAS_DA_SEMANA)))
    REGEXP_DIAS_SEMANA = re.compile('(%s)' % "|".join(Cardapio.DIAS_DA_SEMANA))
    MENSAGEM_ERRO = "Um erro ocorreu."

    def __init__(self, id_mestre, token, port, webhook_url):
        self.id_mestre = id_mestre
        self.token = token
        self.port = port
        self.webhook_url = webhook_url
        self.bandeja = None

    def inicia_bot(self, ):
        self.bandeja = BandejaBot()
        
        app = ApplicationBuilder().token(self.token).connect_timeout(20).pool_timeout(20).get_updates_write_timeout(20).get_updates_read_timeout(20).get_updates_pool_timeout(20).get_updates_connect_timeout(20).connect_timeout(20).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.start))
        app.add_handler(CommandHandler("horarios", self.horarios))
        app.add_handler(CommandHandler("destaque", self.destaques))

        app.add_handler(CommandHandler("almoco", self.almoco))
        app.add_handler(CommandHandler("janta", self.janta))
        app.add_handler(CommandHandler("bandeja", self.bandeja_cmd))

        app.add_handler(CommandHandler("semana", self.semana))

        # Cardapio da semana precisa vir antes
        app.add_handler(MessageHandler(filters.Regex(self.REGEXP_CARDAPIO_SEMANA), \
                        self.cardapio_dia_especifico))
        app.add_handler(MessageHandler(filters.Regex(self.REGEXP_DIAS_SEMANA), \
                        self.refeicoes_dia))

        app.add_handler(MessageHandler(None, self.fallback))
        app.add_error_handler(self.error_handler)

        # TODO setup comandos do bot no statup

        if self.webhook_url is None or not self.webhook_url.strip():
            logging.info("Iniciando em modo pooling")
            app.run_polling()
        else:
            url = f"{self.webhook_url}/{self.token}"
            logging.info("Iniciando em modo Webhook em %s na porta %s", url, self.port)
            app.run_webhook(listen="0.0.0.0", port=self.port, webhook_url=url, url_path=self.token)

    @log_request
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.start(), disable_web_page_preview=True)

    @log_request
    async def horarios(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.horarios())

    @log_request
    async def destaques(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.destaques())

    @log_request
    async def almoco(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.almoco())

    @log_request
    async def janta(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.janta())

    @log_request
    async def bandeja_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(self.bandeja.bandeja())
    
    @log_request
    async def semana(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        texto_resposta, lista_teclado = self.bandeja.opcoes_dias_semana()
        teclado = ReplyKeyboardMarkup(lista_teclado, one_time_keyboard=True, selective=True)
        await update.message.reply_html(texto_resposta, reply_markup=teclado)

    @log_request
    async def refeicoes_dia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        dia_semana = update.message.text
        resposta, lista_teclado = self.bandeja.opcoes_refeicao(dia_semana)
        teclado = ReplyKeyboardMarkup(lista_teclado, one_time_keyboard=True, selective=True)
        await update.message.reply_html(resposta, reply_markup=teclado)

    @log_request
    async def cardapio_dia_especifico(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        cardapio_desejado = update.message.text
        resultado = cardapio_desejado.split(' de ')
        resposta = self.bandeja.cardapio_semana(resultado[0], resultado[1])
        await update.message.reply_html(resposta)

    async def fallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.warning(update.to_json())
        await update.message.reply_html("Comando não reconhecido")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logging.error(str(update))
        await update.message.reply_html(self.MENSAGEM_ERRO)

if __name__ == '__main__':
    import os

    TOKEN = os.getenv("TOKEN")
    ID_MESTRE = os.getenv("ID_MESTRE")

    URL = os.getenv("URL")
    PORT = os.getenv("PORT", 3000)
    PORT = int(PORT) if PORT is not None else None

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    bot = TelegramBot(ID_MESTRE, TOKEN, PORT, URL)
    bot.inicia_bot()
