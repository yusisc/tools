#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# @Time    : 5/4/2018 1:37 PM
# @Author  : yusisc (yusisc@gmail.com)

"""ref
[python]喜马拉雅mp3批量下载工具 | 独自等待-信息安全博客
https://www.waitalone.cn/ximalaya-download.html"""

import requests
import json
import re
import os
from bs4 import BeautifulSoup
import threading
# import subprocess
# import sys
# import time
# from multiprocessing import Pool
import logging

fmt = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)-8s - %(message)s'
logging.basicConfig(level=logging.INFO,
                    format=fmt,
                    filename='./all.log',
                    filemode='a')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(fmt))
logging.getLogger('').addHandler(console)
lgr = logging.getLogger()


class Ximalaya:
    def __init__(self, url, root):
        self.url = url
        self.root = root
        self.url_header = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.url,
            'Cookie': '_ga=GA1.2.1628478964.1476015684; _gat=1',
        }
        self.album_title = None
        self.info_list = []
        self.file_idx = 0

        self.sema = threading.Semaphore(16)
        self.thread_list = []

    def download_file(self, url, file_path):
        self.sema.acquire()
        lgr.info(f'Start downloading {url} -> {file_path}')
        try:
            resp = requests.get(url, headers=self.url_header)
            content = resp.content
            with open(file_path, 'wb') as ff:
                ff.write(content)
            lgr.info(f'Downloading is done for {url}')
        except Exception as error:
            lgr.info(error)
        self.sema.release()
        return 0

    def get_all_album_page(self):
        """
        Get all pages of sound list.
        :return: A list of urls, pages of which content some sound page urls.
        """
        page_list = []
        try:
            response = requests.get(self.url, headers=self.url_header)
            response.encoding = response.apparent_encoding
            html = response.text
        except Exception as msg:
            lgr.info('Can not load the root page.', msg)
        else:
            reg = re.compile(r'<a class="e-\d+ page-link" href="((/\w+){2,}/)"><span class="e-\d+">\d*</span></a>')
            page_button_info = reg.findall(html)
            page_list.extend([tt[0] for tt in page_button_info])
        if page_list:
            return ['http://www.ximalaya.com' + x for x in page_list]
        else:
            return [self.url]

    def analyze_a_track(self, track_id):
        """
        Deal with each audio file.
        :param track_id:
        :return:
        """
        # track_url = f'http://www.ximalaya.com/tracks/{track_id}.json'
        track_url = f'http://www.ximalaya.com/revision/play/tracks?trackIds={track_id}'
        try:
            response = requests.get(track_url, headers=self.url_header)
            response.encoding = response.apparent_encoding
            html = response.text
        except Exception:
            lgr.info(f'Can not load the url: {track_url}.')
            with open('analyze_false.txt', 'ab+') as ff:
                ff.writelines(track_url + '\n')
            return 1
        else:
            json_obj = json.loads(html)
            title = json_obj['data']['tracksForAudioPlay'][0]['trackName']
            title = re.sub("[|\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+", '_', title)
            audio_url = json_obj['data']['tracksForAudioPlay'][0]['src']
            audio_file_name = f'{self.file_idx:03d}_{title.strip()}{audio_url[-4:]}'
            self.file_idx += 1
            audio_file_path = os.path.join(self.root, self.album_title, audio_file_name)
            # download audio file
            thread_temp = threading.Thread(target=self.download_file, args=(audio_url, audio_file_path))
            thread_temp.start()
            self.thread_list.append(thread_temp)
            self.info_list.append(f'{audio_url} ____ {audio_file_path}')
            return 0

    def down_xmly_inlet(self):
        """
        Download inlet
        :return:
        """
        album_page_list = self.get_all_album_page()
        lgr.info(album_page_list)
        for idx, purl in enumerate(album_page_list):
            try:
                response = requests.get(purl, headers=self.url_header)
                response.encoding = response.apparent_encoding
                html = response.text
            except Exception as msg:
                lgr.info('Download page error.', msg)
            else:
                if idx == 0:
                    soup = BeautifulSoup(html, 'lxml')
                    album_title = soup.title.string
                    self.album_title = re.sub("[|\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+", '_', album_title)
                    album_root = os.path.join(self.root, self.album_title)
                    if not os.path.isdir(album_root):
                        os.makedirs(album_root)

                appendixs = re.findall('<a title=".*?" href="(/\w*/\d*/\d*)">.*?</a>', html)
                for appendix in appendixs:
                    id = appendix.split('/')[-1]
                    self.analyze_a_track(id)
        info_path = os.path.join(self.root, self.album_title, 'album.info')
        with open(info_path, 'a+', encoding='utf-8') as ff:
            for info in self.info_list:
                print(info, file=ff)
        for tt in self.thread_list:
            tt.join()
        return 0


if __name__ == '__main__':
    directory_root = '.'
    url_list = [
        'http://www.ximalaya.com/renwen/6414376/',
    ]
    for url in url_list:
        ximalaya = Ximalaya(url=url, root=directory_root).down_xmly_inlet()
