import urllib.request
from bs4 import BeautifulSoup
import logging
import datetime
import string

__author__ = 'gabriel'
LOG_CARDAPIO = 'log/cardapio.log'
CARDAPIO_URL = 'https://docs.google.com/spreadsheets/d/1YvCqBrNw5l4EFNplmpRBFrFJpjl4EALlVNDk3pwp_dQ/pubhtml'
DIAS_DA_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
ORDEM_CARDAPIO = ['Entrada', 'Prato Principal', 'Prato Vegetariano', 'Guarnição',
                  'Acompanhamento', 'Sobremesa', 'Refresco']
ORDEM_REFEICAO = ['Almoço', 'Jantar']
AJUSTE = max([ len(i) for i in ORDEM_CARDAPIO])

def compoe_mensagem(refeicao, dia_semana, dict_refeicao):
    msg = "O %s de %s na UFRJ é:\n" % (refeicao.lower(), dia_semana.lower())
    for prato in ORDEM_CARDAPIO:
        msg += "<b>%s</b>: %s\n" % (prato, dict_refeicao[prato])
    return msg


class Cardapio():
    logging.basicConfig(filename=LOG_CARDAPIO, level=logging.INFO,
                        format='%(asctime)s\t%(levelname)s\t%(message)s')

    def __init__(self):
        self.cardapio = dict()

    def carrega_cardapio(self):
        with urllib.request.urlopen(CARDAPIO_URL) as response:
            html = response.read()
            logging.info("Cardapio lido de " + CARDAPIO_URL)
            soup = BeautifulSoup(html, 'html.parser')

            contador = 0
            for elements in soup.find_all('td', 's3'):
                id_dia_semana = contador % 7
                id_cardapio = (contador // 7) % len(ORDEM_CARDAPIO)
                id_refeicao = contador // (7*len(ORDEM_CARDAPIO))

                dia_semana = DIAS_DA_SEMANA[id_dia_semana]
                prato_cardapio = ORDEM_CARDAPIO[id_cardapio]
                refeicao = ORDEM_REFEICAO[id_refeicao]

                if dia_semana not in self.cardapio:
                    self.cardapio[dia_semana] = dict()
                cardapios_dia = self.cardapio[dia_semana]

                if refeicao not in cardapios_dia:
                    cardapios_dia[refeicao] = dict()
                cardapio_refeicao = cardapios_dia[refeicao]

                if prato_cardapio not in cardapio_refeicao:
                    cardapio_refeicao[prato_cardapio] = dict()
                cardapio_refeicao[prato_cardapio] = elements.contents[0]

                contador += 1
            logging.info("Cardápio: " + str(self.cardapio))


    def __horario(self):
        now = datetime.datetime.today()
        weekday = now.weekday()
        hour = now.hour
        if hour > 14:
            refeicao = 1
        else:
            refeicao = 0
        return ORDEM_REFEICAO[refeicao], DIAS_DA_SEMANA[weekday-1]

    def get_cardapio(self, refeicao, dia):
        return compoe_mensagem(refeicao, dia, self.cardapio[dia][refeicao])

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


if __name__ == '__main__':
    c = Cardapio()
    c.carrega_cardapio()
    print(c.cardapio_mais_proximo())