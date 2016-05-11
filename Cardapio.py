import urllib.request
from bs4 import BeautifulSoup
import logging
import datetime
import re
import json
import hashlib
import threading

__author__ = 'gabriel'
LOG_CARDAPIO = 'log/cardapio.log'
CARDAPIO_URL = 'https://docs.google.com/spreadsheets/d/1YvCqBrNw5l4EFNplmpRBFrFJpjl4EALlVNDk3pwp_dQ/pubhtml'
DIAS_DA_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
ORDEM_CARDAPIO = ['Entrada', 'Prato Principal', 'Prato Vegetariano', 'Guarnição',
                  'Acompanhamento', 'Sobremesa', 'Refresco']
ORDEM_REFEICAO = ['almoço', 'jantar']
MESES_ANO = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto',
             'setembro', 'outubro', 'novembro', 'dezembro']

COMIDAS_IMPORTANTES = ["Kibe", "Quiche", "Almôndegas", "Peixe", "Cocada", "Doce"]

VERBO_SER = ["foi", "é", "será"]
VERBO_TER = ["tivemos", "temos", "teremos"]

REGEXP_TITULO = re.compile('.*Cardápio Semanal - de (?P<inicio>[0-9]+) a [0-9]+ de (?P<mes>[a-zA-Z]+) de (?P<ano>[0-9]+).*')
TEMPO_ATUALIZACAO_AGRESSIVA = 5*60 # 5 minutos
TEMPO_ATUALIZACAO_PROATIVA = 3*60*60 # 3 horas

class Cardapio():
    logging.basicConfig(filename=LOG_CARDAPIO, level=logging.INFO,
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    def __init__(self):
        self.cardapio = dict()
        self.ultima_atualizacao = None
        self.destaques_semana = []
        self.ultima_hash = None

    def conjugacao_verbal(self, dia_semana):
        dia_semana_atual = datetime.datetime.today().weekday()
        id_dia_semana = DIAS_DA_SEMANA.index(dia_semana)

        if id_dia_semana < dia_semana_atual:
            return 0
        if id_dia_semana == dia_semana_atual:
            return 1
        if id_dia_semana > dia_semana_atual:
            return 2

    def __destaca_pratos(self):
        self.destaques_semana = []
        for dia in DIAS_DA_SEMANA:
            for refeicao in ORDEM_REFEICAO:

                destaques_refeicao = []
                for tipo_prato in ORDEM_CARDAPIO:
                    prato_atual = self.cardapio[dia][refeicao][tipo_prato]
                    for comida in COMIDAS_IMPORTANTES:
                        if comida in prato_atual:
                            # indice_inicio_comida = prato_atual.find(comida)
                            # indice_fim_comida = indice_inicio_comida + len(comida)
                            #
                            # prato_destacado = prato_atual[:indice_inicio_comida] + "<b>" + \
                            #                   prato_atual[indice_inicio_comida:indice_fim_comida] +\
                            #                   "</b>" + prato_atual[indice_fim_comida:]
                            prato_destacado = '<b>' + prato_atual  + '</b>'
                            self.cardapio[dia][refeicao][tipo_prato] = prato_destacado
                            destaques_refeicao += [(tipo_prato, prato_destacado)]
                            break
                if len(destaques_refeicao) > 0:
                    self.destaques_semana += [(dia, refeicao, destaques_refeicao)]


    def carrega_cardapio(self):
        with urllib.request.urlopen(CARDAPIO_URL) as response:
            html = response.read()
            logging.info("Cardapio lido de " + CARDAPIO_URL)
            soup = BeautifulSoup(html, 'html.parser')

            cardapio_parseado = dict()
            contador = 0
            for elements in soup.find_all('td', 's3'):
                id_dia_semana = contador % 7
                id_cardapio = (contador // 7) % len(ORDEM_CARDAPIO)
                id_refeicao = contador // (7*len(ORDEM_CARDAPIO))

                dia_semana = DIAS_DA_SEMANA[id_dia_semana]
                prato_cardapio = ORDEM_CARDAPIO[id_cardapio]
                refeicao = ORDEM_REFEICAO[id_refeicao]

                if dia_semana not in cardapio_parseado:
                    cardapio_parseado[dia_semana] = dict()
                cardapios_dia = cardapio_parseado[dia_semana]

                if refeicao not in cardapios_dia:
                    cardapios_dia[refeicao] = dict()
                cardapio_refeicao = cardapios_dia[refeicao]

                if prato_cardapio not in cardapio_refeicao:
                    cardapio_refeicao[prato_cardapio] = dict()
                cardapio_refeicao[prato_cardapio] = elements.contents[0]
                contador += 1

            print("Atualizado")

            # Logica de atualizacao
            cardapio_json = json.dumps(cardapio_parseado, sort_keys=True)
            hash_cardapio = hashlib.sha1(cardapio_json.encode()).hexdigest()

            if hash_cardapio != self.ultima_hash:
                self.cardapio = cardapio_parseado
                self.__destaca_pratos()
                self.ultima_hash = hash_cardapio

                # Na primeira tentativa de atualizacao, tento descobrir a data do cardapio corrente
                if self.ultima_atualizacao == None:
                    titulo = soup.find_all('td', 's0')[0].contents[0]
                    m = REGEXP_TITULO.match(titulo)
                    if m is not None:
                        dia = int(m.group('inicio'))
                        mes = MESES_ANO.index(m.group('mes').lower()) + 1
                        ano = int(m.group('ano'))
                        self.ultima_atualizacao = datetime.datetime(ano, month=mes, day=dia)
                        logging.info("Data de vigência obtida do cardapio: " + str(self.ultima_atualizacao))
                    else: # senao consigo coletar a data, entao assumo que esta atualizado
                        self.ultima_atualizacao = datetime.datetime.today()
                else: # senao for a primeira atualizacao, corrigo a data
                    self.ultima_atualizacao = datetime.datetime.today()

                logging.info("Cardápio atualizado: " + self.ultima_hash)
                logging.info(cardapio_json)
            else:
                logging.info("Cardápio não atualizado, hash igual a anterior")



            self.__agenda_atualizacao()

    def __agenda_atualizacao(self):
        """
            Método auxiliar que agenda atualizacoes
            periodicas de acordo com o grau de desatualizacao
        """
        agora = datetime.datetime.now()

        if self.is_desatualizado() and agora.hour >= 7: # só faz sentido se estamos no horário comercial
            tipo_atualizacao = "agressiva"
            delay = TEMPO_ATUALIZACAO_AGRESSIVA
        else:
            tipo_atualizacao = "proativa"
            delay = TEMPO_ATUALIZACAO_PROATIVA

        threading.Timer(interval=delay, function=self.carrega_cardapio).start()
        logging.info("Proxima atualizacao %s agendada para %s" % (tipo_atualizacao,
                                                                  agora + datetime.timedelta(seconds=delay)))

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
        primeiro_dia_cardapio = self.ultima_atualizacao - datetime.timedelta(self.ultima_atualizacao.weekday())
        return primeiro_dia_cardapio.date()

    def calcula_data_cardapio(self, dia_semana):
        '''
            Calcula a data relativa a um dado dia da semana,
            com relação a semana da ultima data de atualização do cardápio
        '''
        inicio_vigencia = self.data_inicio_vigencia()
        offset_dia_semana = DIAS_DA_SEMANA.index(dia_semana)
        data_cardapio = (inicio_vigencia + datetime.timedelta(offset_dia_semana))
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
        msg = "O %s de %s (%s/%s) na UFRJ %s:\n" % (refeicao.lower(), dia_semana.lower(),
                                                data.day, data.month, VERBO_SER[self.conjugacao_verbal(dia_semana)])
        for prato in ORDEM_CARDAPIO:
            msg += "<i>%s</i>: %s\n" % (prato, dict_refeicao[prato])

        if self.is_desatualizado():
            msg += "\nO cardápio está <b>desatualizado</b>."
        return msg

    def __enumeracao(self, elementos, conectivo_principal = ', ', conectivo_final=' e '):
        if len(elementos) == 1:
            return elementos[0]
        return conectivo_principal.join(elementos[:-1]) + conectivo_final + elementos[-1]

    def compoe_destaques(self):
        if len(self.destaques_semana) == 0:
            return "Esta semana não temos nenhum destaque."
        txt = ""
        for dia, refeicao, destaques_refeicao in self.destaques_semana:
            destaques_txt = self.__enumeracao(["%s (%s)" % (d[1], d[0]) for d in  destaques_refeicao])
            txt += dia.title() + " " + VERBO_TER[self.conjugacao_verbal(dia)]  + " no " + refeicao  + " " + destaques_txt + ".\n"
        return txt

if __name__ == '__main__':
    c = Cardapio()
    c.carrega_cardapio()
    print(c.get_cardapio("almoço", "quarta"))
    print(c.compoe_destaques())