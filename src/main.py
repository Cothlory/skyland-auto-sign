import json
import logging
import os
import time
from datetime import date

import requests

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 2

import push
from skyland import start

exit_when_fail_env = os.environ.get('EXIT_WHEN_FAIL')
use_proxy = os.environ.get('USE_PROXY')

def config_logger():
    current_date = date.today().strftime('%Y-%m-%d')
    if not os.path.exists('logs'):
        os.mkdir('logs')
    logger = logging.getLogger()

    file_handler = logging.FileHandler(f'./logs/{current_date}.log', encoding='utf-8')
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    # console_formatter = logging.Formatter('%(message)s')
    # console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    def filter_code(text):
        filter_key = ['code', 'cred', 'token']
        try:
            j = json.loads(text)
            if not j.get('data'):
                return text
            data = j['data']
            for i in filter_key:
                if i in data:
                    data[i] = '*****'
            return json.dumps(j, ensure_ascii=False)
        except:
            return text

    _get = requests.get
    _post = requests.post

    def _request_with_retry(method_name, request_func, *args, **kwargs):
        if use_proxy:
            kwargs.update({
                'proxies': {
                    'https': 'http://localhost:8000',
                },
                'verify': False
            })

        last_error = None
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                response = request_func(*args, **kwargs)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise requests.exceptions.HTTPError(f'{method_name} returned {response.status_code}')
                logger.debug(f'{method_name.upper()} {args[0]} - {response.status_code} - {filter_code(response.text)}')
                return response
            except requests.exceptions.RequestException as ex:
                last_error = ex
                if attempt == RETRY_COUNT:
                    logger.warning(f'{method_name.upper()} {args[0]} failed after {RETRY_COUNT} attempts: {ex}')
                    raise
                logger.warning(f'{method_name.upper()} {args[0]} attempt {attempt} failed: {ex}, retrying in {RETRY_DELAY_SECONDS}s')
                time.sleep(RETRY_DELAY_SECONDS)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f'{method_name.upper()} request failed without a captured error')

    def get(*args, **kwargs):
        return _request_with_retry('get', _get, *args, **kwargs)

    def post(*args, **kwargs):
        return _request_with_retry('post', _post, *args, **kwargs)

    # 替换 requests 中的方法
    requests.get = get
    requests.post = post


if __name__ == '__main__':
    config_logger()

    print('本项目源代码仓库：https://github.com/xxyz30/skyland-auto-sign(因白嫖action被github封禁)')
    print('https://gitee.com/FancyCabbage/skyland-auto-sign')
    logging.info('=========starting==========')
    start_time = time.time()
    success, all_logs = start()
    push.push(all_logs)
    end_time = time.time()
    logging.info(f'complete with {(end_time - start_time) * 1000} ms')
    logging.info('===========ending============')

    logging.info(f'exit_when_fail_env: {exit_when_fail_env}, success: {success}')
    if (exit_when_fail_env == "on") and not success:
        exit(1)
