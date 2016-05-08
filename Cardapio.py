import urllib.request
from bs4 import BeautifulSoup
import logging
import datetime
import sched
import time
import json
import hashlib

__author__ = 'gabriel'
LOG_CARDAPIO = 'log/cardapio.log'
CARDAPIO_URL = 'https://docs.google.com/spreadsheets/d/1YvCqBrNw5l4EFNplmpRBFrFJpjl4EALlVNDk3pwp_dQ/pubhtml'
DIAS_DA_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
ORDEM_CARDAPIO = ['Entrada', 'Prato Principal', 'Prato Vegetariano', 'Guarnição',
                  'Acompanhamento', 'Sobremesa', 'Refresco']
ORDEM_REFEICAO = ['Almoço', 'Jantar']
#HORARIO_FUNCIONAMENTO =



class Cardapio():
    logging.basicConfig(filename=LOG_CARDAPIO, level=logging.INFO,
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    def __init__(self):
        self.cardapio = dict()
        self.ultima_atualizacao = None
        self.ultima_hash = 0

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

            self.cardapio = cardapio_parseado

            # Logica de atualizacao
            cardapio_json = json.dumps(self.cardapio, sort_keys=True)
            hash_cardapio = hashlib.sha1(cardapio_json.encode()).hexdigest()
            if hash_cardapio != self.ultima_atualizacao:
                self.ultima_hash = hash_cardapio
                self.ultima_atualizacao = datetime.datetime.today()
                logging.info("Cardápio atualizado: " + self.ultima_hash)
                logging.info(cardapio_json)
            else:
                logging.info("Cardápio não atualizado, hash igual ao anterior")

            # Agendador de atualizacao

            # sc = sched.scheduler(time.time, time.sleep)
            # proxima_atualizacao = self.__calcula_tempo_atualizacao()
            # sc.enterabs(time=proxima_atualizacao, priority=1, action=self.carrega_cardapio)
            # sc.run()
            # logging.info("Proxima atualizacao agendada para ", proxima_atualizacao)

    def __calcula_tempo_atualizacao(self):
        # se ja atualizou na semana, entao proxima atualizacao agendada para segunda 8:00
        proxima_segunda = datetime.timedelta(7 - self.ultima_atualizacao)

        # senao conseguiu atualizar na segunda, entao proxima atualizacao agendada para daqui a 10 minutos

        return 10

    def calcula_data_cardapio(self, dia_semana):
        '''
            Calcula a data relativa a um dado dia da semana,
            com relação a semana da ultima data de atualização do cardápio
        '''
        primeiro_dia_cardapio = self.ultima_atualizacao - datetime.timedelta(self.ultima_atualizacao.weekday())
        offset_dia_semana = DIAS_DA_SEMANA.index(dia_semana)
        data_dia_semana = (primeiro_dia_cardapio + datetime.timedelta(offset_dia_semana)).date()
        return "%s/%s" % (data_dia_semana.day, data_dia_semana.month)


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
        msg = "O %s de %s (%s) na UFRJ é:\n" % (refeicao.lower(), dia_semana.lower(),
                                                self.calcula_data_cardapio(dia_semana))
        for prato in ORDEM_CARDAPIO:
            msg += "<b>%s</b>: %s\n" % (prato, dict_refeicao[prato])
        return msg

if __name__ == '__main__':
    c = Cardapio()
    c.carrega_cardapio()
    print(c.cardapio_mais_proximo())