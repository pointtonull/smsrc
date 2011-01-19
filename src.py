#!/usr/bin/python
# -*- coding: UTF-8 -*-
import smtplib
import poplib
import os
import sys
import time
import re

from subprocess import Popen, PIPE
from decoradores import FunctionList 
from debug import debug

COMANDOS = FunctionList()

RC_FILE = os.environ["HOME"] + "/.srcrc"
KEYS_FILE = os.environ["HOME"] + "/.srckeys"
LOG_FILE = os.environ["HOME"] + "/.srclog"

def convertir(cadena):
    teclas = {
        "." : "1", "," : "1" * 2, "¿" : "1" * 3, "a" : "2", "b" : "2" * 2,
        "c" : "2" * 3, "d" : "3", "e" : "3" * 2, "f" : "3" * 3, "g" : "4",
        "h" : "4" * 2, "i" : "4" * 3, "j" : "5", "k" : "5" * 2, "l" : "5" * 3,
        "m" : "6", "n" : "6" * 2, "o" : "6" * 3, "p" : "7", "q" : "7" * 2,
        "r" : "7" * 3, "s" : "7" * 4, "t" : "8", "u" : "8" * 2, "v" : "8" * 3,
        "w" : "9", "x" : "9" * 2, "y" : "9" * 3, "z" : "9" * 4, " " : "0"}

    return "".join((teclas.get(c, c) for c in cadena.lower()))


def get_config():
    try:
        rc = open(RC_FILE)

    except IOError:
        print "No se pudo leer %s" % RC_FILE
        raise

    else:
        preconf = dict((l.strip().split(":") for l in rc.readlines()))
        rc.close()

        conf = {
            "popserver" : preconf.get("popserver", "").strip(),
            "popuser" : preconf.get("popuser", "").strip(),
            "poppass" : preconf.get("poppass", "").strip(),
            "smtpserver" : preconf.get("smtpserver", "").strip(),
            "responseto" : preconf.get("responseto", "").strip(),
        }

        conf["smtpuser"] = preconf.get("smtpuser", conf["popuser"])
        conf["smtppass"] = preconf.get("smtppass", conf["poppass"])

        return conf


def get_mensajes():
    """apop dele getwelcome host list noop pass_ port quit retr rpop
    rset set_debuglevel stat timestamp top uidl user welcome """

    POP3 = poplib.POP3(CONF["popserver"])
    POP3.user(CONF["popuser"])
    POP3.pass_(CONF["poppass"])

    cantidad = len(POP3.list()[1])

    mensajes = []

    for numero in range(1, cantidad + 1):
        mensajes.append("\n".join(POP3.retr(numero)[1]))

    for numero in xrange(1, cantidad + 1):
        POP3.dele(numero)

    POP3.quit()
    debug(mensajes)
    return mensajes


def loguear(texto):
        try:
            log = open(LOG_FILE, "a")
        except IOError:
            try:
                log = open(LOG_FILE, "w")
            except:
                raise

        log.write(time.ctime() + ": " + str(texto) + "\n")
        log.close()


def verify_key(key):
    keysfile = open(KEYS_FILE)
    keys = [k.strip() for k in keysfile.readlines()]
    keysfile.close()

    if key in keys:
        keys.remove(key)
        keysfile = open(KEYS_FILE, "w")
        keysfile.write("\n".join(keys))
        keysfile.close()
        return True
    else:
        return True
        return False


def enviar(mensaje):
    fromaddr = CONF["smtpuser"]
    toaddr = CONF["responseto"]
    subject = "src-Milva"

    server = smtplib.SMTP()
    server.set_debuglevel(0)
    server.connect(CONF["smtpserver"])
    server.ehlo()
    server.starttls()
    server.login(CONF["smtpuser"], CONF["smtppass"])

    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (\
            fromaddr,\
            toaddr,\
            subject,\
            mensaje\
           ))

    server.sendmail(fromaddr, toaddr, msg)
    server.close()


def ejecutar(linea):
    cmd = linea.split()[0]
    args = linea.lstrip(cmd).strip()

    cmd = cmd.lower()

    if cmd in COMANDOS:
        loguear("Ejecutando: %s %s" % (cmd, args))
        return COMANDOS[cmd](args)
    else:
        loguear(cmd + ": no es un comando reconocido")
        return 2



@COMANDOS
def exe(args):
    return os.system(args)


@COMANDOS
def si(args):
    resultado = ejecutar(args)
    if resultado:
        return enviar("%s: %d" % (args, resultado))
    else:
        return None


@COMANDOS
def bti(args):
    bti = Popen("bti", shell=True, stdin=PIPE)
    bti.stdin.write(args.strip() + " #sms")
    bti.stdin.close()
    return bti.returncode


def main():

    mensajes = get_mensajes()

    for mensaje in mensajes:
        regex = (r"""Subject: (?P<titulo>.*?)\n.*?^$(?P<cuerpo>.*)"""
            """CTI MOVIL SMS E-MAIL""")
        match = re.search(regex, mensaje,  re.MULTILINE|re.DOTALL)

        titulo = match.group('titulo')
        cuerpo = match.group('cuerpo')

        if verify_key(convertir(titulo)):
            for linea in (l for l in cuerpo.split("\n") if l.strip()):
                return ejecutar(linea)
        else:
            loguear("Clave no valida: -%s-%s-" % (titulo, convertir(titulo)))
            return 1


CONF = get_config()

if __name__ == "__main__":
    main()
