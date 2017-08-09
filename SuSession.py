from requests import Session
from urllib import parse
from bs4 import BeautifulSoup
from math import floor

class SuSessionError(Exception):
	def __init__(self, value):
		self.value=value

class SuSession(Session):
	SU_LOGIN_HOST = 'weblogin.stanford.edu'
	SU_LOGIN_URL = 'https://weblogin.stanford.edu/login'

	def __init__(self, site, username, password, *args, **kwargs):
		Session.__init__(self, *args, **kwargs)

		site_host = parse.urlparse(site).netloc
		response = self.get(site, allow_redirects=True)

		weblogin_url = parse.urlparse(response.url)
		params = parse.parse_qs(weblogin_url.query)
		if weblogin_url.netloc != 'weblogin.stanford.edu':		
			for p in params:
				if 'idp.stanford.edu' in params[p][0]:
					response = self.get(params[p][0])
					weblogin_url = parse.urlparse(response.url)
					params = parse.parse_qs(weblogin_url.query)
					break
			else:
				raise SuSessionError('Not a site that requires SU authentication')


		#Construct login form data
		login_data = {
			'RT' : params['RT'][0],
			'ST' : params['ST'][0],
			'login' : 'yes',
			'username' : username,
			'password' : password,
			'remember_login' : 'yes',
			'Submit' : 'Login'
		}

		#Modify request headers
		self.headers.update({
			'Referer' : weblogin_url.geturl(),
			'Host' : SuSession.SU_LOGIN_HOST
		})

		#Post form data
		response = self.post(SuSession.SU_LOGIN_URL, data=login_data)

		#Extract into dictionary the two-step form data from the response
		resp_html = BeautifulSoup(response.text, 'lxml')
		device_dict = {}
		form = resp_html.find(id='push-send') #get the push authentication form
		for i_tag in form.find_all('input',{'type' : 'hidden'}):
			device_dict[i_tag.get('name')] = i_tag.get('value')

		#Post two-step auth data to send auth request to smartphone
		self.headers.update({'Referer' : SuSession.SU_LOGIN_URL})
		response = self.post(SuSession.SU_LOGIN_URL, data=device_dict, allow_redirects=False) #Turn off redirect so it will not immediately redirect to remedy website

		#Instead just get the request header information from remedy website to get the JSESSION cookie value
		self.headers.update({'Host' : site_host})
		self.head(response.headers['Location'], allow_redirects=True)
