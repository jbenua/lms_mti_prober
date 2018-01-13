import time
import requests
import logging
from pyquery import PyQuery as pq

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mti.py')


ID = '2331'
D_ID = '2777'
TEST_QUESTIONS = {}

LOGIN_URL = "https://lms.mti.edu.ru/local/login.php"
DISCIPLINE_URL = (
    'https://lms.mti.edu.ru/course/view.php?'
    'id={ID}&disciplineid={D_ID}')
ATTEMPTS_URL = 'https://lms.mti.edu.ru/mod/quiz/view.php'
START_URL = 'https://lms.mti.edu.ru/mod/quiz/startattempt.php'


def get_session():
    s = requests.Session()

    r = s.post(LOGIN_URL, data={
        "username": "harumm.scarumm@gmail.com",
        "password": "oscopes1"
    })
    if r.status_code == requests.codes.ok:
        logger.info("Auth ok")
        return s
    else:
        logger.warn("Failed to auth, try in 10 secs...")
        time.sleep(10)
        return get_session()


def main():

    # login
    s = get_session()
    r = s.get(DISCIPLINE_URL.format(ID=ID, D_ID=D_ID))
    d = pq(r.text)

    # get the last accessible training
    test_url = pq(d('a.training')[-2]).attr('href')

    # accept rules
    r = s.get(test_url)
    data = {}
    for i in pq(pq(r.text)((
            'div.singlebutton > form[method="post"] '
            '> div > input[type="hidden"]'))):
        p = pq(i)
        data[p.attr("name")] = p.attr("value")

    # start test
    r = s.post(ATTEMPTS_URL, data)

    data = {}
    for i in pq(r.text)('form[method="post"] > div > input[type="hidden"]'):
        p = pq(i)
        data[p.attr("name")] = p.attr("value")

    r = s.post(START_URL, data)

    full_text = r.text
    questions = pq(full_text)('div.que > div.content > div.formulation')

    for q in questions:
        p = pq(q)

        text = p('div.qtext').text()
        if text not in TEST_QUESTIONS:
            TEST_QUESTIONS[text] = {'result': None,
                                    'answers': list(),
                                    'iter': 1,
                                    'multi': False}
            answers = p('div.answer > div')

            for a in answers:
                pa = pq(a)
                a_text = pa('label').text()
                if pa('input').attr("type") == "radio":
                    TEST_QUESTIONS[text].multi = False
                TEST_QUESTIONS[text]['answers'].append(a_text)

        attempt = {}
        if TEST_QUESTIONS[text]['result']:
            attempt = TEST_QUESTIONS[text]['result']
        else:
            variant = (
                bin(TEST_QUESTIONS[text]['iter'])[2:]).zfill(
                len(TEST_QUESTIONS[text]['answers']))
            for (index, item) in enumerate(TEST_QUESTIONS[text]['answers']):
                attempt[item] = variant[index]
        answers = p('div.answer > div')

        for a in answers:

            pa = pq(a)
            a_text = pa('label').text()
            pa = pa('input').attr(
                'checked', 'true' if attempt[a_text] == '1' else 'false')
        if not TEST_QUESTIONS[text]['multi']:
            TEST_QUESTIONS[text]['iter'] = TEST_QUESTIONS[text]['iter'] << 1
        else:
            TEST_QUESTIONS[text]['iter'] += 1
            #
            # begin test
            # accept rules
            # shuffle answers

            # post answers
            # check accuracy


# -----------------------------3533007347819314351001058393
# Content - Disposition: form - data; name = "q16143576:13_:flagged"
# 0
# -----------------------------3533007347819314351001058393
# Content - Disposition: form - data; name = "q16143576:13_:flagged"
# 0
# -----------------------------3533007347819314351001058393
# Content - Disposition: form - data; name = "q16143576:13_:sequencecheck"
# 1
# -----------------------------3533007347819314351001058393
# Content - Disposition: form - data; name = "q16143576:13_answer"
# 4        - ## value of the input with answer


# -----------------------------3908362292114915363229560165
# Content - Disposition: form - data; name = "q16143576:3_:sequencecheck"
# 2  # miltucheck
# -----------------------------3908362292114915363229560165
# Content - Disposition: form - data; name = "q16143576:3_choice1"
# 1     # checked
# -----------------------------3908362292114915363229560165
# Content - Disposition: form - data; name = "q16143576:12_choice0"
# 0     # not checked

    time.sleep(60)


if __name__ == "__main__":
    main()
