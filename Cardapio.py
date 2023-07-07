import datetime
import hashlib
import json
import logging
import re
import threading
import urllib.request

from bs4 import BeautifulSoup

MSG_ERRO_CARDAPIO = """
        Um erro ocorreu durante a inicialização do Bot, favor tente novamente daqui a alguns minutos.
        """
DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
ORDEM_CARDAPIO = [
    "Entrada",
    "Prato Principal",
    "Prato Vegetariano",
    "Guarnição",
    "Acompanhamento",
    "Sobremesa",
]
ORDEM_REFEICAO = ["almoço", "jantar"]
MESES_ANO = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

COMIDAS_IMPORTANTES = [
    "Kibe",
    "Quiche",
    "Almôndegas",
    "Peixe",
    "Estrogonofe",
    "Nhoque",
    "Farofa",
]

VERBO_SER = ["foi", "é", "será"]
VERBO_TER = ["tivemos", "temos", "teremos"]

# Constantes do scrapping
CARDAPIO_URL = "https://docs.google.com/spreadsheets/d/1YvCqBrNw5l4EFNplmpRBFrFJpjl4EALlVNDk3pwp_dQ/pubhtml"
REGEXP_TITULO_MEIO_MES = re.compile(
    r"de (?P<inicio>\d+) a \d+ de (?P<mes>\w+) de (?P<ano>\d+)"
)
REGEXP_TITULO_INICIO_MES = re.compile(
    r"de (?P<inicio>\d+) de (?P<mes>\w+) a \d+ de \w+ de (?P<ano>\d+)"
)
REGEXP_BLANK_SPACE = re.compile(r"[\s]+")
REFEICAO_TR_OFFSET = [3, 11]
TD_OFFSET = 1
CLASSE_TABLE = "waffle"
CLASSE_TITULO = "s0"

# Tempos de atualizacao
TEMPO_ATUALIZACAO_AGRESSIVA = 5 * 60  # 5 minutos
TEMPO_ATUALIZACAO_PROATIVA = 3 * 60 * 60  # 3 horas
HORA_INICIO_ATUALIZACAO_AGRESSIVA = (
    8  # apartir das 8 horas comeco a tentar atualizar agressivamente
)


class Cardapio:
    def __init__(self):
        self.cardapio = None
        self.ultima_atualizacao = None
        self.data_cardapio = None
        self.destaques_semana = []
        self.ultima_hash = None

    def __destaca_pratos(self):
        """
        Varre o cardápio em busca de palavras-chaves pré-definidas, realiza o "destaque em HTML"
        no cardápio e salva uma lista dos destaques.
        """
        self.destaques_semana = []
        for dia in DIAS_DA_SEMANA:
            for refeicao in ORDEM_REFEICAO:
                destaques_refeicao = []
                for tipo_prato in ORDEM_CARDAPIO:
                    prato_atual = self.cardapio[dia][refeicao][tipo_prato]
                    for comida in COMIDAS_IMPORTANTES:
                        if comida in prato_atual:
                            prato_destacado = "<i>" + prato_atual + "</i>"
                            self.cardapio[dia][refeicao][tipo_prato] = prato_destacado
                            destaques_refeicao += [(tipo_prato, prato_destacado)]
                            break
                if len(destaques_refeicao) > 0:
                    self.destaques_semana += [(dia, refeicao, destaques_refeicao)]

    def __scrap_refeicao(self, table_rows, id_dia_semana, id_refeicao):
        """
        Faz o scrapping de um dia da semana e refeicao especificos.
        Retorna um dicionario contendo as comidas por prato.
        """
        tr_offset = REFEICAO_TR_OFFSET[id_refeicao]
        refeicao_dict = dict()
        for id_prato_cardapio in range(len(ORDEM_CARDAPIO)):
            row = table_rows[tr_offset + id_prato_cardapio]
            elem = row.find_all("td")[TD_OFFSET + id_dia_semana]

            comida = elem.get_text()
            prato = ORDEM_CARDAPIO[id_prato_cardapio]
            refeicao_dict[prato] = comida
        return refeicao_dict

    def __scrap_informacoes_cardapio(self, html):
        """
        Efetiva o scrapping do cardapio e da data de vigencia, retornando ambos.
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", CLASSE_TABLE)
        table_rows = table.find_all("tr")
        cardapio_coletado = dict()
        for id_dia_semana in range(len(DIAS_DA_SEMANA)):
            dia_semana = DIAS_DA_SEMANA[id_dia_semana]
            cardapio_coletado[dia_semana] = dict()
            for id_refeicao in range(len(ORDEM_REFEICAO)):
                refeicao = ORDEM_REFEICAO[id_refeicao]
                cardapio_coletado[dia_semana][refeicao] = self.__scrap_refeicao(
                    table_rows, id_dia_semana, id_refeicao
                )
        data_titulo = self.__scrap_data_titulo(soup)
        return cardapio_coletado, data_titulo

    def __scrap_data_titulo(self, soup):
        """
        Coleta a data do titulo do cardápio via expressao regular.
        Retorna None senao foi possivel obter esta informacao.
        """
        titulo = soup.find("td", CLASSE_TITULO).get_text()
        titulo = REGEXP_BLANK_SPACE.sub(" ", titulo)
        m = REGEXP_TITULO_INICIO_MES.search(titulo)
        if m is None:
            m = REGEXP_TITULO_MEIO_MES.search(titulo)
        if m is not None:
            dia = int(m.group("inicio"))
            mes = MESES_ANO.index(m.group("mes").lower()) + 1
            ano = int(m.group("ano"))
            return datetime.datetime(ano, month=mes, day=dia)
        return None

    def carrega_cardapio(self):
        """
        Coordena o scraping do cardapio, o destaque de pratos e inicia a logica de atualizacao periodica do cardapio
        """
        try:
            with urllib.request.urlopen(CARDAPIO_URL) as response:
                html = response.read()
                logging.info("Cardapio lido de %s", CARDAPIO_URL)
                cardapio, data_cardapio = self.__scrap_informacoes_cardapio(html)

            # Logica de atualizacao
            cardapio_json = json.dumps(cardapio, sort_keys=True)
            hash_cardapio = hashlib.sha1(cardapio_json.encode()).hexdigest()

            if hash_cardapio != self.ultima_hash:
                self.cardapio = cardapio
                self.__destaca_pratos()
                self.ultima_hash = hash_cardapio
                self.ultima_atualizacao = datetime.datetime.today()

                # Se por qualquer motivo nao consegui a data do cardapio, utilizo a data corrente
                if data_cardapio is None:
                    self.data_cardapio = self.ultima_atualizacao
                    logging.info(
                        "Nao foi possivel obter data do cardapio, usando data corrente: %s",
                        str(self.data_cardapio),
                    )
                else:
                    self.data_cardapio = data_cardapio
                    logging.info(
                        "Data de vigência obtida do cardapio: %s",
                        str(self.data_cardapio),
                    )

                logging.info("Cardápio atualizado: %s", self.ultima_hash)
                logging.info(cardapio_json)
            else:
                logging.info("Cardápio não atualizado, hash igual ao anterior")
            self.__agenda_atualizacao()
        except Exception as e:
            logging.warning(
                "Ocorreu um erro, agendando atualizacao agressiva. %s", str(e)
            )
            self.__agenda_atualizacao(urgente=True)

    def __agenda_atualizacao(self, urgente=False):
        """
        Método auxiliar que agenda atualizacoes
        periodicas de acordo com o grau de desatualizacao
        """
        agora = datetime.datetime.now()
        if urgente:
            delay = TEMPO_ATUALIZACAO_AGRESSIVA
            tipo_atualizacao = "agressiva"
        else:
            if self.is_desatualizado():
                if agora.hour >= HORA_INICIO_ATUALIZACAO_AGRESSIVA:
                    tipo_atualizacao = "agressiva"
                    delay = TEMPO_ATUALIZACAO_AGRESSIVA
                else:
                    # calcula delay ate hora programada
                    delay = (
                        agora.replace(
                            hour=HORA_INICIO_ATUALIZACAO_AGRESSIVA, minute=0, second=0
                        )
                        - agora
                    ).seconds
            else:
                tipo_atualizacao = "proativa"
                delay = TEMPO_ATUALIZACAO_PROATIVA

        threading.Timer(interval=delay, function=self.carrega_cardapio).start()
        logging.info(
            "Proxima atualizacao %s agendada para %s",
            tipo_atualizacao,
            agora + datetime.timedelta(seconds=delay),
        )

    def is_desatualizado(self):
        """
        Verifica se o cardapio esta desatualizado por mais de uma semana,
        de acordo com a data de inicio de vigência
        """
        agora = datetime.datetime.now()
        inicio_vigencia = self.data_inicio_vigencia()
        atraso_atualizacao = agora.date() - inicio_vigencia
        return atraso_atualizacao.days >= 7

    def data_inicio_vigencia(self):
        """
        Calcula a segunda-feira da semana da última data de atualização
        """
        primeiro_dia_cardapio = self.data_cardapio - datetime.timedelta(
            self.data_cardapio.weekday()
        )
        return primeiro_dia_cardapio.date()

    def calcula_data_cardapio(self, dia_semana):
        """
        Calcula a data relativa a um dado dia da semana,
        com relação a semana da ultima data de atualização do cardápio
        """
        inicio_vigencia = self.data_inicio_vigencia()
        offset_dia_semana = DIAS_DA_SEMANA.index(dia_semana)
        data_cardapio = inicio_vigencia + datetime.timedelta(offset_dia_semana)
        return data_cardapio

    def __horario(self):
        now = datetime.datetime.today()
        weekday = now.weekday()
        hour = now.hour
        if hour > 14:
            refeicao = 1
        else:
            refeicao = 0
        return ORDEM_REFEICAO[refeicao], DIAS_DA_SEMANA[weekday]

    def get_cardapio(self, refeicao, dia):
        if self.cardapio is None:
            return MSG_ERRO_CARDAPIO
        return self.compoe_mensagem(refeicao, dia, self.cardapio[dia][refeicao])

    def janta_hoje(self):
        _, dia = self.__horario()
        refeicao = ORDEM_REFEICAO[1]
        return self.get_cardapio(refeicao, dia)

    def almoco_hoje(self):
        _, dia = self.__horario()
        refeicao = ORDEM_REFEICAO[0]
        return self.get_cardapio(refeicao, dia)

    def cardapio_mais_proximo(self):
        refeicao, dia = self.__horario()
        return self.get_cardapio(refeicao, dia)

    def compoe_mensagem(self, refeicao, dia_semana, dict_refeicao):
        data = self.calcula_data_cardapio(dia_semana)
        msg = "O %s de %s (%s/%s) na UFRJ %s:\n" % (
            refeicao.lower(),
            dia_semana.lower(),
            data.day,
            data.month,
            VERBO_SER[self.__conjugacao_verbal(dia_semana)],
        )
        for prato in ORDEM_CARDAPIO:
            msg += "<b>%s</b>: %s\n" % (prato, dict_refeicao[prato])

        if self.is_desatualizado():
            msg += "\nO cardápio está <b>desatualizado</b>."
        return msg

    def __enumeracao(self, elementos, conectivo_principal=", ", conectivo_final=" e "):
        if len(elementos) == 1:
            return elementos[0]
        return (
            conectivo_principal.join(elementos[:-1]) + conectivo_final + elementos[-1]
        )

    def __conjugacao_verbal(self, dia_semana):
        """
        Verifica se dia corrente é passado ou futuro de uma dada data
        """

        if self.is_desatualizado():
            # sempre será passado se estiver desatualizado
            return 0
        if self.ultima_atualizacao.date() < self.data_inicio_vigencia():
            # sempre será futuro caso o cardapio esteja adiantado
            return 2

        dia_semana_atual = datetime.datetime.today().weekday()
        id_dia_semana = DIAS_DA_SEMANA.index(dia_semana)

        if id_dia_semana < dia_semana_atual:
            return 0
        if id_dia_semana == dia_semana_atual:
            return 1
        if id_dia_semana > dia_semana_atual:
            return 2

    def compoe_destaques(self):
        if len(self.destaques_semana) == 0:
            return "Esta semana não temos nenhum destaque."
        txt = ""
        for dia, refeicao, destaques_refeicao in self.destaques_semana:
            destaques_txt = self.__enumeracao(
                ["%s (%s)" % (d[1], d[0]) for d in destaques_refeicao]
            )
            txt += dia.title() + " (" + refeicao + "): " + destaques_txt + ".\n"
        return txt


if __name__ == "__main__":
    c = Cardapio()
    c.carrega_cardapio()
    print(c.get_cardapio("almoço", "quarta"))
    print(c.compoe_destaques())
