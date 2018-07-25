# -*- coding: utf-8 -*-

"""
UC#02: Main critics
Extract the main critics from the customers (top negative opinions)
"""

import pandas as pd
import requests, json, re, sys
import numpy as np

class DictanovaAPIAuth(requests.auth.AuthBase):
	"""Attaches Dictanova Bearer Authentication to the given Request object."""
	
	def __init__(self, id, secret):
		self.apiclient_id = id
		self.apiclient_secret = secret
		self._token = None
	
	def __eq__(self, other):
		return all([
			self.apiclient_id == getattr(other, 'apiclient_id', None),
			self.apiclient_secret == getattr(other, 'apiclient_secret', None)
		])
	
	def __ne__(self, other):
		return not self == other
	
	def __call__(self, r):
		r.headers['Authorization'] = self.get_token()
		return r
	
	def get_token(self):
		# Get authentication token
		if self._token is None:
			payload = {
				"clientId": self.apiclient_id,
				"clientSecret": self.apiclient_secret
			}
			r = requests.post("https://api.dictanova.io/v1/token", json=payload)
			self._token = r.json()
		# Always use the one in cache
		return "Bearer %s" % self._token["access_token"]

if __name__ == "__main__":
	# Prepare Auth handler with API client id and secret
	# https://docs.dictanova.io/docs/authentication-and-security
	clientId, clientSecret = open("../credentials", "r").readline().strip().split(";")
	dictanova_auth = DictanovaAPIAuth(clientId, clientSecret)
	
	############################################################ TOP OPINION / WORDCLOUD
	# Request for top negative opinions
	r = requests.post(
		"https://api.dictanova.io/v1/search/datasets/5b55b264dbcd8100019f0495/terms?opinions=NEGATIVE",
		data="", # empty query
		auth=dictanova_auth)
	print(r)
	top_opinions = r.json()['items']

	####################################################################### WORDCLOUD
	# Word cloud
	# pip3 install wordcloud
	from wordcloud import WordCloud
	import matplotlib.pyplot as plt
	from matplotlib import colors
	onlyred = colors.ListedColormap(['orangered'])
	wc_freq = {opinion["label"]:opinion["occurrences"] for opinion in top_opinions}
	wc = WordCloud(
		prefer_horizontal=1, 
		font_path='Geomanist-Regular.otf',
		background_color="white", 
		colormap=onlyred)
	wordcloud = wc.fit_words(wc_freq)
	plt.imshow(wordcloud)
	plt.axis("off")
	plt.show()
	
	####################################################################### ILLUSTRATE
	# Give an illustration of each opinion
	print("Top 10 negative opinions extracts")
	for i, opinion in enumerate(top_opinions[:10]):
		# Pretty print results
		print("\n\n#%02d [%2d occ.]\t%s" % (i+1, opinion["occurrences"], opinion["id"]))
		query = {
			"field": "TERMS",
			"operator": "EQ",
			"value": opinion["id"],
			"opinion": "NEGATIVE"
		}
		# Top cooccurrences
		r = requests.post(
			"https://api.dictanova.io/v1/search/datasets/5b55b264dbcd8100019f0495/terms",
			json=query,
			auth=dictanova_auth)
		print("mainly found around:\n%s" % ", ".join([o["label"] for o in r.json()["items"][1:20]]))
		# Search for extracts
		r = requests.post(
			"https://api.dictanova.io/v1/search/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth)
		# Pretty print extracts
		print("examples:")
		for i,doc in enumerate(r.json()["items"]):
			# identify occurrences
			highlights = [o for o in doc["enrichments"] if (o["term"]==opinion["id"] and o["opinion"]=="NEGATIVE")]
			highlights = sorted(highlights, key=lambda h: h["offset"]["begin"])
			begin = highlights[0]["offset"]["begin"]
			end = highlights[0]["offset"]["end"]
			txt = doc["content"]
			res = txt[begin-50:begin] + "**" + txt[begin:end] + "**" + txt[end:end+50]
			print("[%s]\t[...]" % doc["externalId"] + re.sub("\s+", " ", res) + "[...]")
			if i > 10: break
# 			splitted = []
# 			last=0
# 			for highlight in highlights:
# 				splitted.append( doc["content"][last:highlight["offset"]["begin"]] )
# 				splitted.append( doc["content"][highlight["offset"]["begin"]:highlight["offset"]["end"]] )
# 				last=highlight["offset"]["end"]
# 			splitted.append(doc["content"][last:])
# 			print("**".join(splitted))
	
	