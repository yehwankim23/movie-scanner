import datetime
import random
import string
import sys
import time
import traceback

import bs4
import requests
import stem
import stem.control
import telegram.ext

CHAT_ID = str(int(""))
TOKEN = ""
PASSWORD = ""

ESCAPE_CHARACTERS = "\\_*[]()~`>#+-=|{}.!"

BOT = telegram.Bot(TOKEN)

scan_count = ""
run_scanner = True

CONTROLLER = stem.control.Controller.from_port(port=9051)

PC_CGV = "http://www.cgv.co.kr"
PC_SHOWTIMES = "/common/showtimes/iframeTheater.aspx?areacode=01&theatercode="
THEATER_CODE = "0013"
PC_DATE = "&date="
QUERY = "&screencodes=&screenratingcode=&regioncode="

headers = {
    "Accept": "text/html,"
              "application/xhtml+xml,"
              "application/xml;q=0.9,"
              "image/avif,"
              "image/webp,"
              "image/apng,"
              "*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Connection": "keep-alive",
    "Cookie": "",
    "DNT": "1",
    "Referer": "",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/102.0.0.0 "
                  "Safari/537.36"
}

PROXIES = {
    "http": "socks5://127.0.0.1:9050",
    "https": "socks5://127.0.0.1:9050"
}

initial_run = True

movies = dict()

PLATFORM_LIST = ["IMAX", "4DX", "SCREENX"]

MOBILE_CGV = "https://m.cgv.co.kr/WebApp/Reservation/QuickResult.aspx?mgc="
MOBILE_THEATER = "&tc="
MOBILE_DATE = "&ymd="

CHANNEL_READY = str(int("-1001702507019"))
CHANNEL_PRIVATE = str(int("-1001689871860"))
CHANNEL_IMAX = "@cgvys_imax"
CHANNEL_4DX = "@cgvys_4dx"
CHANNEL_SCREENX = "@cgvys_screenx"

CHANNEL_LIST = [CHANNEL_READY, CHANNEL_PRIVATE, CHANNEL_IMAX, CHANNEL_4DX, CHANNEL_SCREENX]

check_running = -1


def escape(text):
    for character in ESCAPE_CHARACTERS:
        text = text.replace(character, "\\" + character)

    return text


def send_message(text, chat_id=CHAT_ID):
    BOT.send_message(chat_id, text, "MarkdownV2", disable_web_page_preview=True)


def send_error_message():
    global check_running

    stack_traces = traceback.format_exc().splitlines()
    error_message = stack_traces[1].strip() + "()\n\n" + stack_traces[2].strip() + "\n\n"

    if len(stack_traces) > 4:
        error_message += stack_traces[3].strip() + "()\n\n" + stack_traces[4].strip() + "\n\n"

    send_message(escape(error_message + stack_traces[-1]))
    check_running = -1


def get_session_id():
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(24))


def get_wmon_id():
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(11))


def set_cookie(referer):
    global headers

    headers["Cookie"] = "ASP.NET_SessionId=" + get_session_id() + "; WMONID=" + get_wmon_id()
    headers["Referer"] = referer


def change_ip():
    CONTROLLER.signal(stem.Signal.NEWNYM)


def get_soup(url):
    global headers

    set_cookie(url)
    change_ip()

    time.sleep(3)

    response = requests.get(url, headers=headers, proxies=PROXIES)
    return bs4.BeautifulSoup(response.text, "html.parser")


def find(tag, name, class_=None):
    if class_ is None:
        return tag.find(name, recursive=False)

    return tag.find(name, class_=class_, recursive=False)


def find_all(tag, name, class_=None):
    if class_ is None:
        return tag.find_all(name, recursive=False)

    return tag.find_all(name, class_=class_, recursive=False)


def check_maintenance(soup):
    global initial_run

    if soup.title is None or soup.title.string.strip() != "시스템 점검":
        return False

    p = find(soup.body, "p")
    time_info = p.string.strip().split()[7]

    today = datetime.datetime.now()
    difference = (datetime.datetime(today.year, today.month, today.day, int(time_info[0:2]),
                                    int(time_info[3:5])) - today).total_seconds()

    if difference >= 0:
        if initial_run:
            send_message("CGV 홈페이지 시스템 점검 중입니다")
        else:
            for channel in CHANNEL_LIST:
                send_message("CGV 홈페이지 시스템 점검 중입니다", channel)

        time.sleep(difference)
    else:
        raise Exception("difference < 0")

    return True


def get_dates(soup):
    showtimes_wrap = find(soup.body, "div", "showtimes-wrap")
    sect_schedule = find(showtimes_wrap, "div", "sect-schedule")
    slider = find(sect_schedule, "div", "slider")
    item_wrap_list = find_all(slider, "div", "item-wrap")

    dates = list()

    for item_wrap in item_wrap_list:
        item = find(item_wrap, "ul", "item")
        item_li_list = find_all(item, "li")

        for item_li in item_li_list:
            day = find(item_li, "div", "day")
            a = find(day, "a")

            if a is None:
                continue

            href = a["href"]
            index = href.find("date=")
            dates.append(href[index + 5:index + 13])

    return dates


def check_schedule(soup, date):
    global scan_count, movies, initial_run

    showtimes_wrap = find(soup.body, "div", "showtimes-wrap")
    sect_schedule = find(showtimes_wrap, "div", "sect-schedule")
    slider = find(sect_schedule, "div", "slider")
    item_wrap_list = find_all(slider, "div", "item-wrap")

    selected_date = ""

    for item_wrap in item_wrap_list:
        item = find(item_wrap, "ul", "item")
        item_li = find(item, "li", "on")

        if item_li is None:
            continue

        day = find(item_li, "div", "day")
        a = find(day, "a")

        href = a["href"]
        index = href.find("date=")
        selected_date = href[index + 5:index + 13]

    if date != selected_date:
        return

    date_str = date[0:4] + "년 " + date[4:6] + "월 " + date[6:8] + "일"
    message_ready = date_str
    message_private = date_str
    message_imax = date_str
    message_4dx = date_str
    message_screenx = date_str

    if movies.get(date_str) is None:
        movies.update({date_str: dict()})

    movies_date = movies.get(date_str)

    sect_showtimes = find(showtimes_wrap, "div", "sect-showtimes")
    sect_showtimes_ul = find(sect_showtimes, "ul")
    sect_showtimes_ul_li_list = find_all(sect_showtimes_ul, "li")

    count = 0

    for sect_showtimes_ul_li in sect_showtimes_ul_li_list:
        col_times = find(sect_showtimes_ul_li, "div", "col-times")
        info_movie = find(col_times, "div", "info-movie")
        a = find(info_movie, "a")
        strong = find(a, "strong")

        title = strong.string.strip()

        type_hall_list = find_all(col_times, "div", "type-hall")

        for type_hall in type_hall_list:
            count += 1

            info_hall = find(type_hall, "div", "info-hall")
            info_hall_ul = find(info_hall, "ul")
            info_hall_ul_li_list = find_all(info_hall_ul, "li")

            screentype = find(info_hall_ul_li_list[1], "span", "screentype")

            if screentype is None:
                platform = info_hall_ul_li_list[1].string.strip()

                if PLATFORM_LIST[2] in platform:
                    platform = PLATFORM_LIST[2]
            else:
                platform = find(screentype, "span").string.strip()

            if platform not in PLATFORM_LIST:
                continue

            theater = info_hall_ul_li_list[0].string.strip()
            total_seats = info_hall_ul_li_list[2].string.strip()[1:].strip()[:-1]
            message_title = escape("\n\n" + title + "\n" + theater + " | 총 " + total_seats + "석")

            info = title + " | " + theater + " | 총 " + total_seats + "석"

            if movies_date.get(info) is None:
                movies_date.update({info: dict()})

            movies_info = movies_date.get(info)

            info_timetable = find(type_hall, "div", "info-timetable")
            info_timetable_ul = find(info_timetable, "ul")
            info_timetable_ul_li_list = find_all(info_timetable_ul, "li")

            print_title = True

            for info_timetable_ul_li in info_timetable_ul_li_list:
                a = find(info_timetable_ul_li, "a")

                status = "오픈/매진/마감"

                if a is None:
                    start_time = find(info_timetable_ul_li, "em")

                    movies_info.update({start_time: status})
                    continue

                href = a["href"]

                if href == "/":
                    if platform == PLATFORM_LIST[2]:
                        break

                    # TODO: .contents -> find()
                    start_time = a.contents[0].contents[0]
                    end_time = a.contents[2].contents[1].contents[0][3:]

                    time_info = start_time + "~" + end_time
                    status = "준비중"
                    links = ""
                else:
                    start_string = a["data-playstarttime"]
                    end_string = a["data-playendtime"]

                    start_time = start_string[0:2] + ":" + start_string[2:4]
                    end_time = end_string[0:2] + ":" + end_string[2:4]

                    time_info = start_time + "~" + end_time

                    href_pc = PC_CGV + href

                    index = href.find("MOVIE_CD_GROUP=")
                    href_mobile = MOBILE_CGV + href[index + 15:index + 23] + MOBILE_THEATER \
                                  + THEATER_CODE + MOBILE_DATE + date

                    links = "[__PC__](" + href_pc + ") [__모바일__](" + href_mobile + ")"

                if movies_info.get(start_time) == "오픈/매진/마감":
                    continue

                movies_info.update({start_time: status})

                if print_title:
                    print_title = False

                    if href == "/":
                        if platform != PLATFORM_LIST[2]:
                            message_ready += message_title
                    else:
                        if platform != PLATFORM_LIST[2]:
                            message_private += message_title

                        if platform == PLATFORM_LIST[0]:
                            message_imax += message_title
                        elif platform == PLATFORM_LIST[1]:
                            message_4dx += message_title
                        elif platform == PLATFORM_LIST[2]:
                            message_screenx += message_title

                message_time = escape("\n" + time_info)

                if href == "/":
                    if platform != PLATFORM_LIST[2]:
                        message_ready += message_time + escape(" | 준비중")
                else:
                    if platform != PLATFORM_LIST[2]:
                        message_private += message_time

                        if links != "":
                            message_private += escape(" | ") + links

                    if platform == PLATFORM_LIST[0]:
                        message_imax += message_time
                    elif platform == PLATFORM_LIST[1]:
                        message_4dx += message_time
                    elif platform == PLATFORM_LIST[2]:
                        message_screenx += message_time

    scan_count += "\n" + date_str + ": " + str(count)

    if not initial_run:
        if message_ready != date_str:
            send_message(message_ready, CHANNEL_READY)

        if message_private != date_str:
            send_message(message_private, CHANNEL_PRIVATE)

        if message_imax != date_str:
            send_message(message_imax, CHANNEL_IMAX)

        if message_4dx != date_str:
            send_message(message_4dx, CHANNEL_4DX)

        if message_screenx != date_str:
            send_message(message_screenx, CHANNEL_SCREENX)


def main():
    global scan_count, run_scanner, movies, initial_run, check_running

    # noinspection PyBroadException
    try:
        CONTROLLER.authenticate(password=PASSWORD)
        send_message("Scanner started")
    except Exception:
        send_error_message()
        send_message("Scanner stopped")
        sys.exit(-1)

    while True:
        # noinspection PyBroadException
        try:
            start_time = datetime.datetime.now()

            scan_count = "\n"

            if run_scanner:
                url = PC_CGV + PC_SHOWTIMES + THEATER_CODE + PC_DATE + QUERY
                soup = get_soup(url)

                if check_maintenance(soup):
                    continue

                ereyesterday = start_time - datetime.timedelta(2)
                date_str = str(ereyesterday.year) + "년 " + str(ereyesterday.month) + "월 " \
                           + str(ereyesterday.day) + "일"

                if movies.get(date_str) is not None:
                    movies.pop(date_str)

                dates = get_dates(soup)

                check_schedule(soup, dates[0])

                for date in dates[1:]:
                    url = PC_CGV + PC_SHOWTIMES + THEATER_CODE + PC_DATE + date + QUERY
                    soup = get_soup(url)
                    check_schedule(soup, date)

                initial_run = False
            else:
                scan_count += "\nrun_scanner = False"

            end_time = datetime.datetime.now()

            if check_running != end_time.hour:
                check_running = end_time.hour

                CONTROLLER.authenticate(password=PASSWORD)

                elapsed_time = int((end_time - start_time).total_seconds())
                elapsed_seconds = elapsed_time % 60
                send_message(escape("Scanner running - " + str(elapsed_time // 60) + ":"
                                    + ("0" if elapsed_seconds < 10 else "") + str(elapsed_seconds)
                                    + scan_count))
        except Exception:
            send_error_message()

    send_message("Scanner stopped")


if __name__ == "__main__":
    main()
