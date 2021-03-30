import logging
import requests
import time

from pyquery import PyQuery as pq
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mti.py')


ID = ''
D_ID = ''

LOGIN_URL = 'https://lms.mti.edu.ru/local/login.php'
DISCIPLINE_URL = (
    'https://lms.mti.edu.ru/course/view.php?id={ID}&disciplineid={D_ID}'
)
ATTEMPTS_URL = 'https://lms.mti.edu.ru/mod/quiz/view.php'
START_URL = 'https://lms.mti.edu.ru/mod/quiz/startattempt.php'
POST_ANSWERS_URL = 'https://lms.mti.edu.ru/mod/quiz/processattempt.php'


LOGIN = ''
PSWD = ''

TEST_QUESTIONS = {}


def make_attempt(q):
    attempt = {}
    if q['result']:
        attempt = q['result']
    else:
        variant = bin(q['iter'])[2:].zfill(
            len(q['answers'])
        )
        for (item, value) in zip(q['answers'], variant):
            attempt[item] = value
    return attempt


class Prober:

    def __init__(self, questions=None):
        self.session = None
        if questions:
            self.questions = questions
        else:
            self.questions = {}

    def shuffle_results(self, err_q):
        for q in self.questions:
            if self.questions[q]['result'] is None:
                if q in err_q:
                    if not self.questions[q]['multi']:
                        self.questions[q]['iter'] = (
                            self.questions[q]['iter'] << 1
                        )
                    else:
                        self.questions[q]['iter'] += 1

                    if (
                        len(self.questions[q]['answers'])
                        < len(bin(self.questions[q]['iter'])[2:])
                    ):
                        self.questions[q]['iter'] = 1
                elif not self.questions[q]['result']:
                    attempt = {}
                    variant = bin(self.questions[q]['iter'])[2:].zfill(
                        len(self.questions[q]['answers'])
                    )
                    for (item, value) in zip(
                            self.questions[q]['answers'],
                            variant
                    ):
                        attempt[item] = value
                    self.questions[q]['result'] = attempt

    def get_session(self):
        if self.session:
            self.session = self.session.close()
        s = requests.Session()
        s.headers.update(
            {'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/63.0.3239.132 Safari/537.36')})

        r = s.post(LOGIN_URL, data={'username': LOGIN, 'password': PSWD})

        while r.status_code != requests.codes.ok:
            logger.error('Failed to auth, retry in 5 secs...')
            time.sleep(5)
            r = s.post(LOGIN_URL, data={'username': LOGIN, 'password': PSWD})
        logger.info('Auth ok')
        self.session = s

    def get_training_url(self):
        r = self.session.get(DISCIPLINE_URL.format(ID=ID, D_ID=D_ID))
        while r.status_code != requests.codes.ok:
            logger.error('Failed to get discipline, retry in 5 secs...')
            time.sleep(5)
            r = self.session.get(DISCIPLINE_URL.format(ID=ID, D_ID=D_ID))
        d = pq(r.text)
        return pq(d('a.training')[-2]).attr('href')

    def accept_rules(self, url):
        r = self.session.get(url)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to get training, retry in 5 secs...')
            time.sleep(5)
            r = self.session.get(url)
        data = {}
        for i in pq(pq(r.text)(
            'div.singlebutton '
            '> form[method="post"] '
            '> div '
            '> input[type="hidden"]'
        )):
            p = pq(i)
            data[p.attr('name')] = p.attr('value')
        return data

    def start_attempt(self, args):
        r = self.session.post(ATTEMPTS_URL, args)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to start attempt, retry in 5 secs...')
            time.sleep(5)
            r = self.session.post(ATTEMPTS_URL, args)

        data = {}
        for i in pq(r.text)(
            'form[method="post"] '
            '> div '
            '> input[type="hidden"]'
        ):
            p = pq(i)
            data[p.attr('name')] = p.attr('value')
        return data

    def do_test(self, args):
        r = self.session.post(START_URL, args)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to start test, retry in 5 secs...')
            time.sleep(5)
            r = self.session.post(START_URL, args)

        full_text = r.text
        questions = pq(full_text)('div.que > div.content > div.formulation')

        data = []
        for q in questions:
            p = pq(q)
            sq_name = pq(p('h3+input[type="hidden"]')).attr('name')
            sq_val = pq(p('h3+input[type="hidden"]')).attr('value')
            name = sq_name.split('_')[0] + '_:flagged'
            data += [(name, '0'), (name, '0'), (sq_name, sq_val)]

            text = p('div.qtext').text()
            if text not in self.questions:
                self.questions[text] = {
                    'result': None,
                    'answers': list(),
                    'iter': 1,
                    'multi': False,
                }
                answers = p('div.answer > div')

                for a in answers:
                    pa = pq(a)
                    a_text = pa('label').text()
                    if pa('input').attr('type') != 'radio':
                        self.questions[text]['multi'] = True
                    self.questions[text]['answers'].append(a_text)

            answers = p('div.answer > div > div')
            for a in answers:
                pa = pq(pq(a)('label')).text()
                if pa not in self.questions[q]['answers']:
                    self.questions[q]['answers'] = [
                        pa] + self.questions[q]['answers']

            attempt = make_attempt(self.questions[text])
            answers = p('div.answer > div')
            for a in answers:
                pa = pq(a)
                a_text = pa('label').text()
                i_name = pa('input[type!="hidden"]').attr('name')
                if attempt[a_text] == '1':
                    pa('input').attr('checked', 'true')
                    if self.questions[text]['multi']:
                        data.append((i_name, '1'))
                    else:
                        data.append(
                            (i_name, pa('input[type!="hidden"]').val()))

        hidden = pq(full_text)(
            'form#responseform > div'
        ).children('input[type="hidden"]')
        for h in hidden:
            ph = pq(h)
            data.append((ph.attr('name'), ph.attr('value')))
        return data

    def post_answers(self, data):
        mdata = MultipartEncoder(data)

        headers = self.session.headers
        headers.update({'Content-Type': mdata.content_type})
        r = self.session.post(POST_ANSWERS_URL, data=mdata,
                              headers=headers)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to post answers, retry in 5 secs...')
            time.sleep(5)
            r = self.session.post(POST_ANSWERS_URL, data=mdata,
                                  headers=headers)
        args = []
        ph = pq(r.text)('form[method="post"] > div > input[type="hidden"]'
                        )
        for p in ph:
            h = pq(p)
            args.append((h.attr('name'), h.attr('value')))
        return args

    def submit_answers(self, args):
        args = OrderedDict(args)

        a = {
            'attempt': args['attempt'],
            'finishattempt': '1',
            'sesskey': args['sesskey'],
            'timeup': '0',
            'slots': '',
        }
        headers = self.session.headers
        headers.update({
            'Referer': (
                'https://lms.mti.edu.ru/mod/quiz/attempt.php?attempt=%s' % (
                    args['attempt']))
        })

        r = self.session.post(POST_ANSWERS_URL, params=a,
                              headers=headers)
        while r.status_code != requests.codes.ok:

            logger.error('Failed to submit answers, retry in 5 secs...')
            time.sleep(5)
            r = self.session.post(POST_ANSWERS_URL, args,
                                  headers=headers)
        return

    def get_result_table_url(self):
        r = self.session.get(DISCIPLINE_URL.format(ID=ID, D_ID=D_ID))
        while r.status_code != requests.codes.ok:
            logger.error('Failed to get discipline, retry in 5 secs...')
            time.sleep(5)
            r = self.session.get(DISCIPLINE_URL.format(ID=ID,
                                                       D_ID=D_ID))
        d = pq(r.text)
        return pq(d('a.training:last'))('a').attr('href')

    def get_result_url(self, url):
        r = self.session.get(url)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to get table, retry in 5 secs...')
            time.sleep(5)
            r = self.session.get(url)
        d = pq(r.text)
        return pq(d('table.attempt_table tr:last td.lastcol a'
                    )).attr('href')

    def get_results(self, url):
        r = self.session.get(url)
        while r.status_code != requests.codes.ok:
            logger.error('Failed to get results, retry in 5 secs...')
            time.sleep(5)
            r = self.session.get(url)
        err_q = [pq(q).text() for q in
                 pq(r.text)('ul.protocol_themelist_questions li')]

        logger.debug("Errors: %s", err_q)
        logger.debug(self.questions)

        self.shuffle_results(err_q)
        # for q in self.questions:
        #     if q in err_q:
        #         if self.questions[q]['result'] != None:
        #             logger.error(
        #                 "WTF, result `%s` %s was ok, but not now!", q, self.questions[q])
        #         self.questions[q]['result'] = None
        #         if not self.questions[q]['multi']:
        #             self.questions[q]['iter'] = self.questions[q]['iter'] << 1
        #         else:
        #             self.questions[q]['iter'] += 1

        #         if len(self.questions[q]['answers']) < len(
        #                 bin(self.questions[q]['iter'])[2:]):
        #             self.questions[q]['iter'] = 1
        #     else:
        #         attempt = {}
        #         variant = bin(self.questions[q]['iter'])[2:].zfill(
        #             len(self.questions[q]['answers']))
        #         for (item, value) in zip(self.questions[q]['answers'], variant):
        #             attempt[item] = value
        #         self.questions[q]['result'] = attempt

    def run(self):
        first = True
        logger.info("%s %s", all([self.questions[q]['result'] is not None
                                  for q in self.questions]), first)
        while (
                (not all([self.questions[q]['result'] is not None
                          for q in self.questions]))
                or first
        ):
            try:
                if not first:
                    time.sleep(150)
                else:
                    first = False
                self.get_session()
                training_url = self.get_training_url()
                attempt_args = self.accept_rules(training_url)
                start_args = self.start_attempt(attempt_args)
                data = self.do_test(start_args)
                args = self.post_answers(data)
                self.submit_answers(args)
                result_table_url = self.get_result_table_url()
                result_url = self.get_result_url(result_table_url)
                self.get_results(result_url)
            except Exception as e:
                logger.critical('FAILED: %s', e)
                print(self.questions)
                return


def main():
    p = Prober(TEST_QUESTIONS)
    try:
        p.run()
    except KeyboardInterrupt:
        print(p.questions)
        return
    print(p.questions)


if __name__ == '__main__':
    main()
