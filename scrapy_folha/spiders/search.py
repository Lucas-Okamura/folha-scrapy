# -*- coding: utf-8 -*-
import scrapy
from scrapy_folha.items import ScrapyFolhaItem
import pandas as pd
from datetime import timedelta
import datetime
import os

class SearchSpider(scrapy.Spider):

    def __init__(self):
      self.i = 0

    name = 'search'
    allowed_domains = ['search.folha.uol.com.br', 
                        'www1.folha.uol.com.br',
                        'f5.folha.uol.com.br',
                        'guia.folha.uol.com.br',
                        'agora.folha.uol.com.br']

    start_urls = ['https://search.folha.uol.com.br/search?q=*']

    def parse_date(self, date_str):
      month_dict = {
        'jan' : 1,
        'fev' : 2,
        'mar' : 3,
        'abr' : 4,
        'mai' : 5,
        'jun' : 6,
        'jul' : 7,
        'ago' : 8,
        'set' : 9,
        'out' : 10,
        'nov' : 11,
        'dez' : 12
      }
      day, month_name, year  = date_str.strip().split('.')
      month = month_dict[month_name]

      return datetime.datetime(int(year), month, int(day))

    def parse(self, response):
      
      last_date = pd.to_datetime('today')
      min_date = pd.to_datetime('2017-10-02')
      for li in response.css("li#view-view.c-headline.c-headline--newslist"):
        link = li.css("a ::attr(href)").extract_first()
        dates = pd.Series(response.css('time.c-headline__dateline::attr(datetime)').getall()).str[:11]
        dates = dates.apply(self.parse_date)
        last_date = dates.min()

        yield response.follow(link, self.parse_article)

      next_page = response.css("li.c-pagination__arrow a::attr(href)").extract()

      if (self.i == 0 and next_page is not None) or (self.i > 0 and len(next_page) > 1):
        self.i = self.i + 1

        yield response.follow(next_page[-1], self.parse)

      elif last_date > min_date:
        self.i = 0
        last_date = last_date - timedelta(days = 1)
        min_date_year_str = str(min_date.year)
        min_date_month_str = str(min_date.month).zfill(2)
        min_date_day_str = str(min_date.day).zfill(2)
        last_date_year_str = str(last_date.year)
        last_date_month_str = str(last_date.month).zfill(2)
        last_date_day_str = str(last_date.day).zfill(2)
        new_filter_link = f'https://search.folha.uol.com.br/search?q=*&periodo=personalizado&sd={min_date_day_str}%2F{min_date_month_str}%2F{min_date_year_str}&ed={last_date_day_str}%2F{last_date_month_str}%2F{last_date_year_str}&site=todos'

        yield response.follow(new_filter_link, self.parse)

    def parse_article(self, response):
      link       = response.url

      # www1.folha.uol.com.br
      if any(domain in link for domain in ['search.folha.uol.com.br', 'www1.folha.uol.com.br']):
        text_html = "div.c-news__body p ::text"
      
      # f5.folha.uol.com.br
      elif 'f5.folha.uol.com.br' in link:
        text_html = "div.j-paywall.news__content.js-news-content.js-disable-copy.js-tweet-selection p ::text"
      
      # agora.folha.uol.com.br
      elif 'agora.folha.uol.com.br' in link:
        text_html = "div.c-news__content p ::text"
      
      # 'guia.folha.uol.com.br'
      elif 'guia.folha.uol.com.br' in link:
        text_html = 'div.js-content-article.js-news-content.js-disable-copy p ::text'

      title      = response.css("article h1 ::text").extract_first()
      text       = "".join(response.css(text_html).extract())
      date       = "".join(response.css('meta[property="article:published_time"]::attr(content)').extract())

      article = ScrapyFolhaItem(title=title, date=date, text=text, link=link, page=self.i)
      yield article
