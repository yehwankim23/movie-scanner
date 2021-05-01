import datetime
import html
import json
import sys
import time
import traceback

import requests
import telegram
import telegram.ext

CHAT_ID = int("")
TOKEN = ""
PASSWORD = ""

BOT = telegram.Bot(TOKEN)

pong = True
run_program = True
SLEEP_SECONDS = 3

URL = "https://www.megabox.co.kr/on/oh/ohc/Brch/schedulePage.do"
data = {
    "masterType": "brch",
    "detailType": "spcl",
    "theabKindCd": "DBC",
    "brchNo": "",
    "firstAt": "Y",
    "playDe": "",
    "brchNo1": "",
    "spclbYn1": "Y",
    "theabKindCd1": "DBC"
}
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/json; charset=UTF-8",
    "DNT": "1",
    "Origin": "https://www.megabox.co.kr",
    "Referer": "https://www.megabox.co.kr/specialtheater/dolby/time",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/103.0.0.0 "
                  "Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": ".Not/A)Brand;v=99, Google Chrome;v=103, Chromium;v=103",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows"
}

movies = dict()
initial_run = True

BRCH_NO_NAMYANGJU = "0019"
BRCH_NO_DAEGU = "7011"
BRCH_NO_DAEJEON = "0028"
BRCH_NO_ANSEONG = "0020"
BRCH_NO_COEX = "1351"
BRCH_NO_LIST = [BRCH_NO_NAMYANGJU, BRCH_NO_DAEGU, BRCH_NO_DAEJEON, BRCH_NO_ANSEONG, BRCH_NO_COEX]

CHANNEL_ID_LIST = {
    BRCH_NO_NAMYANGJU: "@mgbds_namyangju",
    BRCH_NO_DAEGU: "@mgbds_daegu",
    BRCH_NO_DAEJEON: "@mgbds_daejeon",
    BRCH_NO_ANSEONG: "@mgbds_anseong",
    BRCH_NO_COEX: "@mgbds_coex",
}


def send_message(text, chat_id=CHAT_ID):
    BOT.send_message(chat_id, text)


def send_error_message():
    global pong

    stack_traces = traceback.format_exc().splitlines()
    error_message = stack_traces[1].strip() + "()\n\n" + stack_traces[2].strip() + "\n\n"

    if len(stack_traces) > 4:
        error_message += stack_traces[3].strip() + "()\n\n" + stack_traces[4].strip() + "\n\n"

    send_message(error_message + stack_traces[-1])
    pong = True


def say(update, context):
    # noinspection PyBroadException
    try:
        if update.effective_chat.id != CHAT_ID:
            return

        # noinspection PyBroadException
        try:
            password = context.args[0]
        except Exception:
            send_message("Syntax: /say [password] [message]")
            return

        if password != PASSWORD:
            send_message("Incorrect password")
            return

        message = " ".join(context.args[1:])

        for brch_no in BRCH_NO_LIST:
            send_message(message, CHANNEL_ID_LIST[brch_no])
            time.sleep(1)
    except Exception:
        send_error_message()


def ping(update, _):
    global pong

    # noinspection PyBroadException
    try:
        if update.effective_chat.id == CHAT_ID:
            pong = True
    except Exception:
        send_error_message()


def pause(update, context):
    global run_program

    # noinspection PyBroadException
    try:
        if update.effective_chat.id != CHAT_ID:
            return

        # noinspection PyBroadException
        try:
            password = context.args[0]
        except Exception:
            send_message("Syntax: /pause [password]")
            return

        if password != PASSWORD:
            send_message("Incorrect password")
            return

        run_program = False
        send_message("Program paused")
    except Exception:
        send_error_message()


def resume(update, context):
    global run_program

    # noinspection PyBroadException
    try:
        if update.effective_chat.id != CHAT_ID:
            return

        # noinspection PyBroadException
        try:
            password = context.args[0]
        except Exception:
            send_message("Syntax: /resume [password]")
            return

        if password != PASSWORD:
            send_message("Incorrect password")
            return

        run_program = True
        send_message("Program resumed")
    except Exception:
        send_error_message()


def get_mega_map(brch_no, play_de=""):
    global data

    time.sleep(SLEEP_SECONDS)

    data["brchNo"] = brch_no
    data["brchNo1"] = brch_no
    data["playDe"] = play_de
    return json.loads(requests.post(URL, json.dumps(data), headers=HEADERS).text)["megaMap"]


def check_schedule(movie_form_list, brch_no):
    global movies, initial_run

    show_date = True
    show_title = True
    previous_movie_nm = ""
    message = ""

    for movie_form in movie_form_list:
        if movie_form["movieStatCdNm"] != "상영중":
            continue

        play_de = movie_form["playDe"]

        if movies.get(play_de) is None:
            movies.update({play_de: dict()})

        movies_play_de = movies.get(play_de)

        if movies_play_de.get(brch_no) is None:
            movies_play_de.update({brch_no: dict()})

        movies_brch_no = movies_play_de.get(brch_no)
        movie_nm = movie_form["movieNm"]

        if movies_brch_no.get(movie_nm) is None:
            movies_brch_no.update({movie_nm: list()})

        movies_movie_nm = movies_brch_no.get(movie_nm)
        play_start_time = movie_form["playStartTime"]
        play_start_hour = str(int(play_start_time[0:2]) % 24)

        if len(play_start_hour) == 1:
            play_start_hour = "0" + play_start_hour

        play_end_time = movie_form["playEndTime"]
        play_end_hour_int = int(play_end_time[0:2])
        play_end_hour = str(play_end_hour_int % 24)

        if len(play_end_hour) == 1:
            play_end_hour = "0" + play_end_hour

        play_time = play_start_hour + play_start_time[2:] + "~" + play_end_hour + play_end_time[2:]

        if play_time not in movies_movie_nm:
            movies_movie_nm.append(play_time)

            if initial_run:
                continue

            if show_date:
                show_date = False
                message += play_de[0:4] + "년 " + play_de[4:6] + "월 " + play_de[6:8] + "일"

            if movie_nm != previous_movie_nm:
                show_title = True

            if show_title:
                show_title = False

                play_kind_nm = html.unescape(movie_form["playKindNm"])
                tot_seat_cnt = str(movie_form["totSeatCnt"])

                message += "\n\n" + movie_nm + "\n" + play_kind_nm + " | 총 " + tot_seat_cnt + "석"

            message += "\n" + play_time
            previous_movie_nm = movie_nm

    if message != "":
        send_message(message, CHANNEL_ID_LIST[brch_no])


def main():
    global run_program, movies, initial_run, pong

    # noinspection PyBroadException
    try:
        check_running = True

        updater = telegram.ext.Updater(TOKEN)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(telegram.ext.CommandHandler("say", say))
        dispatcher.add_handler(telegram.ext.CommandHandler("ping", ping))
        dispatcher.add_handler(telegram.ext.CommandHandler("pause", pause))
        dispatcher.add_handler(telegram.ext.CommandHandler("resume", resume))

        updater.start_polling()
        send_message("Program started")
    except Exception:
        send_error_message()
        send_message("Program stopped")
        sys.exit(-1)

    while True:
        # noinspection PyBroadException
        try:
            if run_program:
                for brch_no in BRCH_NO_LIST:
                    mega_map = get_mega_map(brch_no)
                    today_date = datetime.datetime.now().strftime("%Y%m%d")
                    ereyesterday = (datetime.datetime(int(today_date[0:4]), int(today_date[4:6]),
                                                      int(today_date[6:8]))
                                    - datetime.timedelta(2)).strftime("%Y%m%d")

                    if movies.get(ereyesterday) is not None:
                        movies.pop(ereyesterday)

                    play_de_list = list()

                    for movie_form_de in mega_map["movieFormDeList"]:
                        play_de_list.append(movie_form_de["playDe"])

                    if today_date in play_de_list:
                        play_de_list.remove(today_date)

                    check_schedule(mega_map["movieFormList"], brch_no)

                    for play_de in play_de_list:
                        check_schedule(get_mega_map(brch_no, play_de)["movieFormList"], brch_no)

            initial_run = False

            if datetime.datetime.now(datetime.timezone.utc).hour % 6 == 0:
                if check_running:
                    check_running = False
                    send_message("Program running")
            else:
                check_running = True

            if pong:
                pong = False
                send_message("Pong")
        except Exception:
            send_error_message()
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
