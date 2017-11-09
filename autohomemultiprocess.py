# -*- coding: utf-8 -*-
import urllib2
import BeautifulSoup
import sys
import re
import MySQLdb
import time
import multiprocessing

class AutohomeCrawler():
    def __init__(self):
        pass
    
    def gethtml(self, url):
        head = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:55.0) Gecko/20100101 Firefox/55.0"}
        request = urllib2.Request(url, headers=head)
        html = urllib2.urlopen(request).read()
        if len(html) == 0:
            print u'没有获取到网页内容！'
        else:
            return html.decode("gbk")
    
    
    
    def getarticle(self, pagenumber):
        articleinfo = {'articlelink': '', 'imagelink': '', 'articletitle': '', 'articlesummary': '', 'articleclick': ''}
        articlelist = []
        # 组装pagenumber对应的url
        url = 'https://www.autohome.com.cn/all/' + str(pagenumber) + '/#liststart'
        # 获取当前页html代码
        html = self.gethtml(url)
        # 解析html文档，获取文章的原文链接、图片链接、标题、简要内容
        soup = BeautifulSoup.BeautifulSoup(html)
        if pagenumber == 1:
            for divtag in soup.findAll('div', {'id': 'auto-channel-lazyload-article', 'class': 'article-wrapper'}):
                for ultag in divtag.findAll('ul', {'class': 'article'}):
                    for articletag in ultag.findAll('li', {'data-artidanchor': re.compile('\d+')}):
                        articleinfo['articlelink'] = articletag.a['href']
                        articleinfo['imagelink'] = articletag.div.img['src']
                        articleinfo['articletitle'] = articletag.h3.string
                        articleinfo['articlesummary'] = articletag.p.string
                        articleinfo['articleclick'] = articletag.em.contents[-1]
                        articlelist.append(articleinfo)
                        articleinfo = {'articlelink': '', 'imagelink': '', 'articletitle': '', 'articlesummary': '',
                                       'articleclick': ''}
        else:
            for divtag in soup.findAll('div', {'id': 'auto-channel-lazyload-article', 'class': 'article-wrapper'}):
                for ultag in divtag.findAll('ul', {'id': 'Ul1', 'class': 'article'}):
                    for articletag in ultag.findAll('li'):
                        articleinfo['articlelink'] = articletag.a['href']
                        articleinfo['imagelink'] = articletag.div.img['src']
                        articleinfo['articletitle'] = articletag.h3.string
                        articleinfo['articlesummary'] = articletag.p.string
                        articleinfo['articleclick'] = articletag.em.contents[-1]
                        articlelist.append(articleinfo)
                        articleinfo = {'articlelink': '', 'imagelink': '', 'articletitle': '', 'articlesummary': '',
                                       'articleclick': ''}
        return articlelist
    
    
    def writetodb(self, articlelist):
        conn = MySQLdb.connect(host='localhost', user='root', passwd='123qwe', db='testdb', port=3306, charset='utf8')
        cur = conn.cursor()
        try:
            cur.execute('''CREATE TABLE IF NOT EXISTS `autohome_171109`(
            `Id` INT UNSIGNED AUTO_INCREMENT,
            `ArticleLink` VARCHAR(100) NOT NULL,
            `ImageLink` VARCHAR(100) NOT NULL,
            `ArticleTitle` VARCHAR(100) NOT NULL,
            `ArticleSummary` VARCHAR(100) NOT NULL,
            `ArticleClick` VARCHAR(20) NOT NULL,
            PRIMARY KEY (`Id`)
            )ENGINE=InnoDB DEFAULT CHARSET=utf8;
            ''')
            conn.commit()
        except:
            conn.rollback()
    
        sqlinsert = 'INSERT INTO autohome_171109(`ArticleLink`, `ImageLink`, `ArticleTitle`, `ArticleSummary`, `ArticleClick`) VALUES (%s, %s, %s, %s, %s);'
        try:
            for i in range(len(articlelist)):
                cur.execute(sqlinsert, (
                    articlelist[i]['articlelink'], articlelist[i]['imagelink'], articlelist[i]['articletitle'],
                    articlelist[i]['articlesummary'], articlelist[i]['articleclick']))
            conn.commit()
        except:
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    def getendpage(self):
        pagelist = []
        # 输入url，获取html界面
        url = 'https://www.autohome.com.cn/all/'
        html = self.gethtml(url)
        # 解析html文档，搜寻到相应的子节点，获取到最后一页的页码
        soup = BeautifulSoup.BeautifulSoup(html)
        for tag in soup.findAll('a', {'target': '_self', 'href': re.compile('/all/\d+/#liststart')})[:-1]:
            pagelist.append(int(tag.string))
        endpage = max(pagelist)
        return endpage

class CrawlThread(multiprocessing.Process):
    def __init__ (self, Crawler, pageQueue, lock):
        multiprocessing.Process.__init__(self)
        self.Crawler = Crawler
        self.pageQueue = pageQueue
        self.lock = lock
    
    def run(self):
        #global lock
        while self.pageQueue.empty() == False:
            self.lock.acquire()
            pagenumber = self.pageQueue.get()
            print u'##   正在爬取第' + str(pagenumber) + u'页的相关内容.  ##'
            articlelist = self.Crawler.getarticle(pagenumber)
            print u'&& 正在将第' + str(pagenumber) + u'页的内容写入数据库. &&'
            self.Crawler.writetodb(articlelist)   
            self.lock.release()
        
if __name__ == '__main__':
    # 设置系统编码方式
    reload(sys)
    sys.setdeaultcoding = 'utf-8'
    print u'######################################'
    print u'##   欢迎进入汽车之家新闻爬取小工具   ##'
    print u'######################################'
    print u'\n'
    Crawler = AutohomeCrawler()
    pageQueue = multiprocessing.Queue(10000)
    lock = multiprocessing.Lock()
    startpage = 1
    # 在html界面中获取最后的页码
    endpage = Crawler.getendpage()
    print u'##   总共获取到' + str(endpage) + u'页文章  ##'
    for i in range(endpage):
        pageQueue.put(i+1)
    for j in range(5):
        p = CrawlThread(Crawler, pageQueue, lock)
        p.daemon = True
        p.start()
        p.join()
        
    
    print u'######################################'
    print u'##     爬取完毕，请在数据库中查看！   ##'
    print u'######################################'
