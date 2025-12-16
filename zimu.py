import requests
import urllib.request
from bs4 import BeautifulSoup
import os
import glob
import re
import time
import codecs
import chardet
import re
import sys
import urllib.parse
import chardet
import random
import fnmatch
import argparse
from tenacity import retry, stop_after_attempt, wait_exponential
from requests.adapters import HTTPAdapter, Retry
#用来下载https://www.subtitlecat.com/的字幕
#如果带参数，那参数就是这个要处理的目录
#输入目录，下载目录下所有的mp4文件


#current_dir = os.path.dirname(__file__)




#mp4_files = [f for f in glob.glob(current_dirr + '\\*.mp4')]
#mp4_files = glob.glob(current_dirr + '\\*.mp4')
#mp4_files = glob.glob('z:\\Avdatahousefrompc6\\gvh-596\\*.mp4')

def extract_between(text, start_delimiter, end_delimiter):
    """
    提取字符串中位于 start_delimiter 和 end_delimiter 之间的内容。
    
    参数:
        text (str): 需要提取子串的原始字符串
        start_delimiter (str): 开始分隔符
        end_delimiter (str): 结束分隔符
    
    返回值:
        str: 分隔符之间的内容，如果未找到分隔符则返回 None 或空字符串（根据需求选择）
    
    示例：
        text = "prefix[start_content]suffix"
        start_delimiter = "[start_"
        end_delimiter = "_]"
        
        result = extract_between(text, start_delimiter, end_delimiter)
        print(result)  # 输出: content
    """
    try:
        start_index = text.index(start_delimiter) + len(start_delimiter)
        end_index = text.index(end_delimiter, start_index)
        return text[start_index:end_index]
    except ValueError:
        return None



def get_mp4_files(directory):
	mp4_files = []

	for root, dirs, files in os.walk(directory):
		for file in fnmatch.filter(files, '*.mp4'):
			mp4size = os.path.getsize(os.path.join(root, file))
			if mp4size > 104857600:#100M
				mp4_files.append(os.path.join(root, file))
		for file in fnmatch.filter(files, '*.avi'):
			mp4size = os.path.getsize(os.path.join(root, file))
			if mp4size > 104857600:#100M
				mp4_files.append(os.path.join(root, file))
		for file in fnmatch.filter(files, '*.wmv'):
			mp4size = os.path.getsize(os.path.join(root, file))
			if mp4size > 104857600:#100M
				mp4_files.append(os.path.join(root, file))
	return mp4_files


def down_file(session,url,headers,file_name):
	response = session.get(url, headers=headers,stream=True)  # 注意设置stream参数为True以便于处理大文件
	if response.status_code == 200:
		with open(file_name, 'wb') as f:
			for chunk in response.iter_content(chunk_size=8192):  # 使用迭代内容的方式逐块下载，chunk大小可以根据需要调整
				f.write(chunk)
			print(f'下载字幕文件成功{file_name}')
		return 0
	else:
		print(f"down title file request failed，status_code : {response.status_code}", flush=True)
		return 1


def replace_symbols_in_file(file_path):
    # 临时文件路径，用于存放修改后的内容
    temp_file = file_path + '.tmp'
    
    with open(file_path, 'r', encoding='ansi',errors='ignore') as infile:
        content = infile.read()
        
    # 使用正则表达式替换所有的 `：` 为 `:`
    content = re.sub(r'：', ':', content)
    
    # 使用正则表达式替换所有的 `->` 为 `—>`
    content = re.sub(r'(\d)->', r'\1 -->', content)
    
    with open(temp_file, 'w', encoding='ansi') as outfile:
        outfile.write(content)
    
    if os.path.isfile(temp_file):
        import shutil
        shutil.move(temp_file, file_path)  # 替换原文件
        print(f"已将 {file_path} 中的 `：` 和 `->` 替换成相应的符号")
    else:
        print("创建临时文件失败")


#filenamenopath = os.path.basename(mp4_files[0])#不包含路径
#mp4_name_nokuozhangming = os.path.splitext(filenamenopath)[0]#没有扩展名的mp4文件，比如，你好adn-163ab.mp4 =》 你好adn-163ab


#print(os.path.basename(mp4_files[0]))  # 输出：MP4 文件的路径列表

def strtofanhao(name):# 你好adn-163ab =>adn-163
	#print(name)
	#如果name里有很多个番号，取番号后面后-的为准
	english_letters = re.findall(r'[a-zA-Z]{2,}', name)
	digits = re.findall(r'\d{3,}', name)
	#print(len(english_letters))
	if len(english_letters) == 0 or len(digits) == 0:
		return ""
	#print(english_letters,digits)
	okfanhao = ""
	okdigit = ""
	for fanhao in english_letters:
		if fanhao + '-' in name:
			okfanhao = fanhao
			break
	for digit in digits:
		if '-' + digit in name:
			okdigit = digit
			break
	if okfanhao != "" and okdigit != "":
		return okfanhao + '-' + okdigit
	if okfanhao != "" and len(digits[0]) > 2:
		return okfanhao + '-' + digits[0]
	if len(english_letters[0]) > 1 and len(digits[0]) > 2:
		return english_letters[0] + '-' + digits[0]
	else:
		return ""

def detect_encoding(file_path):
	with open(file_path, 'rb') as f:
		data = f.read(1024)

	if data.startswith(b'\xef\xbb\xbf'):
		return 'utf-8'
	else:
		encoding = chardet.detect(data)['encoding']
		return encoding

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, max=3))
def fetch_url_with_retry(session, url, headers):
    try:
        response = session.get(url, headers=headers, stream=True, timeout=(15, 15))
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"fetch_An error occurred: {e}", flush=True)
        raise


def downallsrt(str_fanhao,mp4_name_nokuozhangming,savepath,alltds): #如果downstr下载的字幕不符合要求，比如说大小小于10KB，就试着下载所有字幕
	fanhao = str_fanhao.upper()#fanhao 都换成大写，str_fanhao 为原始查询番号，和MP4文件名相关
	host = "https://www.subtitlecat.com/"
	url = "https://www.subtitlecat.com/index.php?search=" + fanhao
		# 常见的 User-Agent 列表
	USER_AGENTS = [
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15',
	]
	# 随机选择一个 User-Agent
	user_agent = random.choice(USER_AGENTS)
	headers = {
		'User-Agent': user_agent,
		'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
		'Referer': 'https://www.subtitlecat.com',
	}
	session = requests.Session()
	retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
	adapter = HTTPAdapter(max_retries=retries)
	session.mount('http://', adapter)
	session.mount('https://', adapter)
	fetch_url_with_retry(session, url, headers)
	pivot = 0
	maxfilesize = 0
	largest_file = None
	for tds in alltds:
		pivot = pivot + 1
		if tds is None:
			continue
		if tds.find('a') is None:
			continue
		if fanhao in tds.a['href'].upper():
			addrupper = tds.a['href']
			addrfinal = host + addrupper
			if fanhao not in addrfinal.upper():
				continue
			for i in range(5):
				try:
					responsefinal = session.get(addrfinal,timeout=(15,15))
					responsefinal.raise_for_status()  # 如果响应状态码不是200，则抛出异常
					print(responsefinal.status_code, flush=True)
					break
				except requests.exceptions.Timeout:
					print(f"second: Request timed out!: {url}", flush=True)
					time.sleep(5)
				except requests.exceptions.RequestException as e:
					print(f"An error occurred: {addrfinal} {e}", flush=True)
					time.sleep(5)
				if i == 4:
					print(f'second: TIME OUT : {addrfinal}', flush=True)
					break
			soupfinal = BeautifulSoup(responsefinal.content,"html.parser",from_encoding='utf-8')
			table = soupfinal.find(attrs={'id': 'download_zh-CN'})
			twtitle = False#默认TW字幕不需要
			if table is None:
			#找不到简体中文，试着找繁体中文
				table = soupfinal.find(attrs={'id': 'download_zh-TW'})
			if table is None:
			#繁体中文找不到，就退出
				print('no chinese subtitle', flush=True)
				continue
			else:
				twtitle = True
			linkdown = host + table.get('href')
			print(linkdown, flush=True)
			linkencode = urllib.parse.quote(linkdown,safe='/:?&=')
			zimuname = os.path.join(savepath,mp4_name_nokuozhangming + '-' + str(pivot) + '.zh-CN.srt')
			if down_file(session,linkencode,headers,zimuname) == 1:#下载失败
				print('##3字幕下载失败###',zimuname)
				#print("pivot= ",pivot)
				continue
			print("pivot= ",pivot)
			file_size_bytes = os.path.getsize(zimuname)
			if file_size_bytes > maxfilesize:
				largest_file = (mp4_name_nokuozhangming,zimuname, savepath,file_size_bytes)  # 存储文件名和其大小
				maxfilesize = file_size_bytes
			transcodeutf2ansi(zimuname)#转码成ansi
			replace_symbols_in_file(zimuname)
			if file_size_bytes < 19000:
				print(f'删除小于19KB的字幕文件:{zimuname}')
				os.remove(zimuname)
	#把下载字幕文件最大的字幕文件改成adn-034-zh-CN.srt
	if int(largest_file[3]) > 19000:
		print(f'把下载字幕最大的文件{largest_file[1]}改名')
		os.rename(largest_file[1],os.path.join(savepath,mp4_name_nokuozhangming) + '.zh-CN.srt')

def downsrt(str_fanhao,mp4_name_nokuozhangming,savepath):#三个参数，要查询的番号和原始MP4文件名，用来保存的字幕和原始mp4文件名对于
	
	# 设置 URL 和查询字符串
	#fanhao = "ADN-106"
	fanhao = str_fanhao.upper()#fanhao 都换成大写，str_fanhao 为原始查询番号，和MP4文件名相关
	host = "https://www.subtitlecat.com/"
	#url = "https://www.subtitlecat.com/subs/180/ADN-306.html"
	url = "https://www.subtitlecat.com/index.php?search=" + fanhao
	#query_string = "adn-252"  # replace with your desired subtitle search term

	# 发送 GET 请求到网站
	
	#zimuname = linkdown.split('/', -1)[-1]
	zimuname = os.path.join(savepath,mp4_name_nokuozhangming + '.zh-CN.srt')
	if os.path.exists(zimuname):
		print('file alreadly exist',zimuname, flush=True)
		return 1
	print('url:',url, flush=True)
	#print('str_fanhao:',str_fanhao)
	print('fanhao:',fanhao, flush=True)
	headerscopy = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0'}
	headerscopy['Accept-Language'] = 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2'
	headerscopy['Referer'] = 'https://www.subtitlecat.com/'
	headerscopy1 = {
	'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43'
	}
	# 常见的 User-Agent 列表
	USER_AGENTS = [
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15',
	]
	# 随机选择一个 User-Agent
	user_agent = random.choice(USER_AGENTS)
	headers = {
		'User-Agent': user_agent,
		'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
		'Referer': 'https://www.subtitlecat.com',
	}

	#response = requests.get(url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0'})
	session = requests.Session()
	retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
	adapter = HTTPAdapter(max_retries=retries)
	session.mount('http://', adapter)
	session.mount('https://', adapter)
	#for i in range(5):
	#	try:
	#		response = session.get(url,headers=headers,stream=True,timeout=(15,15))
	#		response.raise_for_status()  # 如果响应状态码不是200，则抛出异常
	#		break
	#	except requests.exceptions.Timeout:
	#		print(f"first: Request timed out!: {url}", flush=True)
	#	except requests.exceptions.RequestException as e:
	#		print(f"An error occurred: {url} {e}", flush=True)
	#	if i == 4:
	#		print(f'first: TIME OUT ,failed to 5 times try: {url}', flush=True)
	#		return 1
	response = fetch_url_with_retry(session, url, headers)
	if not response:
		return 1
	try:
		soup = BeautifulSoup(response.content, "html.parser")
	except Exception as e:
		print(f"An error occurred while parsing HTML content: {e}",flush=True)
		return 1
	#print(soup)
	#print(fanhao,len(fanhao))
	alltds = soup.find_all('td')
	if not alltds:
		aaa = None
	else:
		aaa = alltds[0]#先取第一个标签
		lastchange = alltds[0]#这个地址保留到最后，如果其他地址出现问题比如有地址但是404错误，就用这个地址试试
		#print(lastchange)
	i = 0
	ifchinesefind = 0
	for tds in alltds:
		if ('from zh-CN' in tds.text or 'from Chinese' in tds.text) and fanhao in tds.a['href'].upper():#对zh-cn的链接感兴趣，而且是第一个链接就可以了，不用继续找其他的
			#print(alltds[i + 1].text,tds.text)
			if i == len(alltds) - 1:
				break
			if alltds[i + 1].text == '\xa0':
				i += 1
				continue
			if alltds[i + 1].i['class'][1] in "fa-thumbs-up":#大拇指向上
				aaa = tds
				ifchinesefind = 1 #找到了中文翻译的字幕
				#print(alltds[i])
				#print(alltds[i + 1].i['class'])
				break
		i += 1
	i = 0
	if ifchinesefind == 0:#可以试试有没有英文翻译的字幕
		for tds in alltds:
			if 'from English' in tds.text and fanhao in tds.a['href'].upper():
				if i == len(alltds) - 1:
					break
				if alltds[i + 1].text == '\xa0':
					i += 1
					continue
				if alltds[i + 1].i['class'][1] in "fa-thumbs-up":#大拇指向上
					aaa = tds
					ifchinesefind = 2 #找到英文的翻译字幕
					break
			i += 1
	i = 0
	if ifchinesefind == 0:#可以试试有没有大拇指的字幕
		for tds in alltds:
			if 'translated from' in tds.text and fanhao in tds.a['href'].upper():
				if i == len(alltds) - 1:
					break
				if alltds[i + 1].text == '\xa0':
					i += 1
					continue
				if alltds[i + 1].i['class'][1] in "fa-thumbs-up":
					aaa = tds
					ifchinesefind = 3 #找到大拇子字幕
					break
			i += 1
	i = 0
	if ifchinesefind == 0:#试试中文+没有大拇指的字幕+下载数目,选取一个下载数量大的字幕
		for tds in alltds:
			if 'from Chinese' in tds.text and fanhao in tds.a['href'].upper():
				if i == len(alltds) - 1:
					break
				if alltds[i + 1].text == '\xa0':
					numberdownloadcn = alltds[i + 2].text
					aaa = tds
					aaacn = tds
					ifchinesefind = 4 #找到中文没有大拇指上和大拇子下的字幕了
					break
			i += 1
		i = 0
		for tds in alltds:#试试英文+没有大拇指的字幕+下载数目
			if 'from English' in tds.text and fanhao in tds.a['href'].upper():
				if i == len(alltds) - 1:
					break
				if alltds[i + 1].text == '\xa0':
					numberdownloaden = alltds[i + 2].text
					aaa = tds
					aaaen = tds
					ifchinesefind = 5 #找到英文没有大拇指上和大拇子下的字幕了
					break
			i += 1
		try:
			numcn = int(numberdownloadcn.split()[0])
			numen = int(numberdownloaden.split()[0])
			if numcn > numen:
				aaa = aaacn
			else:
				aaa = aaaen
		except:
			pass
	if ifchinesefind == 0 or ifchinesefind == 2 or ifchinesefind == 3 or ifchinesefind == 4 or ifchinesefind == 5:
		#字幕名字改成 .nogood-zh.srt,表示字幕是日本或者其他小语种翻译来的，翻译质量不高，以后可以重新下载更好的字幕
		#zimuname = os.path.join(savepath,mp4_name_nokuozhangming + '.zh-CN.srt')
		zimuname = zimuname.replace("zh-CN", "nogood-zh")
	#ttt = soup.find('a',string=fanhao)
	#bbb = soup.find('td',string=str_fanhao)
	if aaa is None:
		print(str_fanhao,'canot find subtitle file', flush=True)
		return 1
	#print(f'找到 td标签里的内容 : {aaa}')
	#print(f'找到 标签里的超链接地址: {aaa.a["href"]}')
	if aaa is not None:
		addrupper = aaa.a['href']
		addrfinal = host + addrupper
		addrupperlastchange = lastchange.a['href']#subs/364/stars-361.html
		addrfinallastchange = host + addrupperlastchange#https://www.subtitlecat.com/subs/364/stars-361.html
		#每个页面，比如https://www.subtitlecat.com/subs/364/stars-361.html，下面都有一个stars-361-orig.srt文件，可以下载
		lastchangefanhao_position = addrfinallastchange.rfind('/')
		lastchangefanhao = addrfinallastchange[lastchangefanhao_position + 1:]#stars-361.html
		dot_html_position = lastchangefanhao.rfind('.html')
		result = lastchangefanhao[:dot_html_position]#stars-361
		milldleurl = extract_between(addrfinallastchange,r'com/',lastchangefanhao)
		lastchangeURL = host + milldleurl + result + '-orig.srt'#https://www.subtitlecat.com/subs/364/stars-361-orig.srt
		#lastchangeURL是网站默认的一个下载地址，在不能获取地址的时候，可以试着用这个地址下载看看的
		#但是比如地址是(translated from Korean)，那这个字幕地址就是韩语了
		print('lastchangeURL :',lastchangeURL)
		#print('aaaaaa'+addrfinallastchange)
	if fanhao not in addrfinal.upper():
		print('the download link dont find the subtitle FAN HAO',addrfinal,fanhao, flush=True)
		return 1
	
	print(addrfinal, flush=True)
	#addrfinal = urllib.parse.quote(addrfinal,safe='★/:?&=')
	# 查找包含字幕结果的表格
	#input('wait')
	for i in range(5):
		try:
			responsefinal = session.get(addrfinal,timeout=(15,15))
			if addrfinal != addrfinallastchange:
				responsefinallastchange = session.get(addrfinallastchange,timeout=(15,15))
			responsefinal.raise_for_status()  # 如果响应状态码不是200，则抛出异常
			print(responsefinal.status_code, flush=True)
			break
		except requests.exceptions.Timeout:
			print(f"second: Request timed out!: {url}", flush=True)
			time.sleep(5)
		except requests.exceptions.RequestException as e:
			print(f"An error occurred: {addrfinal} {e}", flush=True)
			time.sleep(5)
		if i == 4:
			print(f'second: TIME OUT : {addrfinal}', flush=True)
			return 1
	soupfinal = BeautifulSoup(responsefinal.content,"html.parser",from_encoding='utf-8')
	#if addrfinal !=  addrfinallastchange:
	#	soupfinallastchange = BeautifulSoup(responsefinallastchange.content,"html.parser",from_encoding='utf-8')
	#	tablelastchange = soupfinallastchange.find(attrs={'id': 'download_zh-CN'})
	#	linkdownlastchange = host + tablelastchange.get('href')
	#	linkencodelastchange = urllib.parse.quote(linkdownlastchange,safe='/:?&=')
	table = soupfinal.find(attrs={'id': 'download_zh-CN'})
	
	twtitle = False#默认TW字幕不需要
	if table is None:
		#找不到简体中文，试着找繁体中文
		table = soupfinal.find(attrs={'id': 'download_zh-TW'})
		if table is None:
		#繁体中文找不到，就退出
			print('no chinese subtitle', flush=True)
			return 1
		else:
			twtitle = True
	linkdown = host + table.get('href')
	
	print(linkdown, flush=True)
	linkencode = urllib.parse.quote(linkdown,safe='/:?&=')
	
	headersold = {
	'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Language': 'en-US,en;q=0.5',
	# 添加其他需要的 headers
	}
	#if addrfinal == addrfinallastchange:#如果地址相同，但是下载失败，说明这个下载地址获取到，但是404错误的时候，可以用网站默认的orig.srg来试试看
	#	linkencodelastchange = urllib.parse.quote(lastchangeURL,safe='/:?&=')
	#	print('lastchangeURL',linkencodelastchange)
	linkencodelastchange = urllib.parse.quote(lastchangeURL,safe='/:?&=')
	if down_file(session,linkencode,headers,zimuname) == 1:#下载失败
		if down_file(session,linkencodelastchange,headers,zimuname) == 0:
			print('user lastchange for download',linkencodelastchange)
		else:
			return 1
	
	
	file_size_bytes = os.path.getsize(zimuname)
	
	transcodeutf2ansi(zimuname)
	replace_symbols_in_file(zimuname)
	if file_size_bytes < 15000 or downloadallsubtitle :
		print('the download subtitle file size less Nine KB, download all other subtitle files',zimuname, flush=True)
		os.remove(zimuname)
		downallsrt(str_fanhao,mp4_name_nokuozhangming,savepath,alltds)
	

def transcodeutf2ansi(zimuname):
	if detect_encoding(zimuname) == 'utf-8':
		print('transcode utf-8 to ansi',zimuname, flush=True)
		with open(zimuname, 'r', encoding='utf-8', errors='ignore') as f_in:
			content = f_in.read()
			#print(content)
		with codecs.open(zimuname, 'w','ansi',errors='ignore') as ansi_file:#replace
			#f_out = codecs.encode(content.encode('utf-8'), 'ansi')
			#f_out.write(f_out.decode())
			ansi_file.write(content)
			print(f'success ,{zimuname} download', flush=True)



def delete_question_mark(text):
    # 
    #text = '\n'.join([' ' + line for line in text.split('\n')])
    
    # 使用正则表达式（Regular Expression）删除每行开头的问号
    new_text = re.sub(r'^\?', '', text, flags=re.MULTILINE)
    
    return new_text



# 测试函数
#text = "?a???aa?\n?asdfas??f??"
#new_text = delete_question_mark(text)
#print(text)
#print(new_text)

#with open('MIDE-688.1080p.zh-CN.srt','r') as f:
#    f_read = delete_question_mark(f.read())


#with open('new_text.txt', 'w') as f:
#    f.write(f_read)




#fin = strtofanhao(mp4_name_nokuozhangming)
#print(fin)

# 创建 ArgumentParser 对象
parser = argparse.ArgumentParser(description="描述你的脚本用途")
# 添加 -all 选项
parser.add_argument('-all', action='store_true', help='下载所有对应的mp4文件的字幕')
parser.add_argument('-d', '--directory', type=str, help='指定目录路径')
# 解析命令行参数
args = parser.parse_args()
downloadallsubtitle = False
if args.all:
	downloadallsubtitle = True
if args.directory:
	current_dirr = sys.argv[1]
else:
	current_dirr = input('输入要下载字幕的文件夹目录: ')

mp4_files = get_mp4_files(current_dirr)

if len(mp4_files) == 0:
	print('No MP4 file finded: ',current_dirr, flush=True)
	exit(1)
else:
	if len(mp4_files) > 30:#超过30个的mp4文件获取字幕，需要手动确认
		res = input(f'超过30的mp4文件获取字幕，需要手动确认: {len(mp4_files)},请按y继续下载字幕:  ')
		if res != 'y':
			exit(1)
for mp4file in mp4_files:
	filenamenopath = os.path.basename(mp4file)#不包含路径,只有文件名
	last_directory_name = os.path.basename(os.path.dirname(mp4file)) #最后一个目录名
	if last_directory_name.endswith("CH") or last_directory_name.endswith("-C") or last_directory_name.endswith("ch"):
		print('dont need to download srt,',last_directory_name)
		continue
	filenamepath = os.path.dirname(mp4file)
	print(f'try to downlowd subtitle for {mp4file}', flush=True)
	mp4_name_nokuozhangming = os.path.splitext(filenamenopath)[0]#没有扩展名的mp4文件，比如，你好adn-163ab.mp4 =》 你好adn-163ab
	searchfanhaokey = strtofanhao(mp4_name_nokuozhangming)
	if searchfanhaokey != "":
		downsrt(searchfanhaokey,mp4_name_nokuozhangming,filenamepath)
