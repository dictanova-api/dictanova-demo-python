# -*- coding: utf-8 -*-

"""
UC#02: Main critics
Extract the main critics from the customers (top negative opinions)
"""

import pandas as pd
import requests, json, re, sys
import numpy as np
from wordcloud import WordCloud # pip3 install wordcloud
import matplotlib.pyplot as plt
from matplotlib import colors

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

def searchresult2html(output, documents, only=None, meta=None):
	"""
	Generate an html file to highlight semantic enrichments.
	
	output: path to the html file generated
	documents: list of the documents (items in search result)
	only: if specified, the highlith will be limited to only the opinion id in parameter
	meta: a list of metadata to display, if None they no metadata displayed
	"""
	with open(output, "w", encoding="utf-8") as fout:
		# colormap
		colormap = {
			"POSITIVE": "LightGreen",
			"NEGATIVE": "LightCoral",
			"NEUTRAL": "LightGray"
		}
		# header
		fout.write("<!DOCTYPE html>\n")
		fout.write("<html lang=\"en\">\n")
		fout.write("<head>\n<meta charset=\"utf-8\">\n<title>json2html</title>\n</head>\n")
		fout.write("<body style=\"font-family : geomanist; padding:30px; \">\n");
		fout.write("<ul style=\"list-style:none;\">\n");
		# Each document
		for doc in documents:
			# Select enrichments and sort by offset
			if only is None:
				opinions = doc["enrichments"]
			else:
				opinions = [e for e in doc["enrichments"] if e["term"]==only]
			opinions = sorted(opinions, key=lambda e: e["offset"]["begin"])
			# Build html
			fout.write("<li style=\"margin-bottom:20px; border:1px solid gray; padding:10px;\">\n")
			fout.write("<h3>%s</h3>\n" % doc["externalId"])
			if not meta is None:
				fout.write("<ul style=\"list-style:none\">\n")
				mtuples = [(m["code"], m["value"]) for m in doc["metadata"] if m["code"] in meta]
				for code,value in mtuples:
					fout.write("<li style=\"display: inline; font-size: 75%%; font-color: grey\">%s=%s</li>\n" % (code, value))
				fout.write("</ul><br />\n")
			curr_opinion = None
			next_opinion = 0
			fout.write("<p>\n")
			for i,c in enumerate(doc["content"]):
				# handle highlighting
				if (not curr_opinion is None) and (i >= curr_opinion["offset"]["end"]):
					curr_opinion = None
					fout.write("</span>\n")
				elif (next_opinion<len(opinions)) and (opinions[next_opinion]["offset"]["begin"]==i):
					curr_opinion = opinions[next_opinion]
					next_opinion += 1
					if not curr_opinion is None:
						fout.write("<span style=\"background-color: %s\">\n" % colormap[ curr_opinion["opinion"] ])
				# add content
				if c != "\n":
					fout.write(c)
				else:
					fout.write("</ br>\n")
			fout.write("</p></li>\n")
		# footer
		fout.write("</ul>\n</body>\n</html>\n")

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
	
	onlyred = colors.ListedColormap(['orangered'])
	wc_freq = {opinion["label"]:opinion["occurrences"] for opinion in top_opinions}
	wc = WordCloud(
		prefer_horizontal=1, 
		background_color="white", 
		colormap=onlyred)
	wordcloud = wc.fit_words(wc_freq)
	plt.imshow(wordcloud)
	plt.axis("off")
	#plt.show()
	plt.savefig("uc2-top-criticisms.png", bbox_inches='tight')
	
	############################################################### SEARCH FOR FEEDBACKS

	print("Search for feedbacks that contain each top 10 criticisms")
	for i, opinion in enumerate(top_opinions[:10]):
		# Pretty print results
		print("\n\n#%02d [%2d occ.]\t%s" % (i+1, opinion["occurrences"], opinion["id"]))
		# Search for extracts
		query = {
			"field": "TERMS",
			"operator": "EQ",
			"value": opinion["id"],
			"opinion": "NEGATIVE"
		}
		r = requests.post(
			"https://api.dictanova.io/v1/search/datasets/5b55b264dbcd8100019f0495/documents",
			json=query,
			auth=dictanova_auth)
		# Export as html files
		fname = "uc2-search-%s.html"%opinion["label"]
		print("\tExport search results as html: '%s'" % fname)
		searchresult2html(
			fname, 
			r.json()["items"], 
			only=opinion["id"],
			meta=["date_of_purchase", "rating_satisfaction", "category", "subcategory", "vendor", "shop"])

	################################################################ ASSOCIATED OPINIONS
	
	neutral_map = colors.ListedColormap(['darkblue'])
	
	print("Extract opinions associated with each top 10 criticisms")
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
		print("\t%s" % r)
		# Wordcloud
		wc_freq = {op["label"]:op["occurrences"] for op in r.json()["items"] if op["id"]!=opinion["id"]}
		wc = WordCloud(
			prefer_horizontal=1, 
			background_color="white", 
			colormap=neutral_map)
		wordcloud = wc.fit_words(wc_freq)
		plt.imshow(wordcloud)
		plt.title("Opinions mainly associated with criticism '%s'" % opinion["label"])
		plt.axis("off")
		#plt.show()
		print("\tExport associated opinions as wordcloud")
		plt.savefig("uc2-opinions-associated-with%s.png"%opinion["label"], bbox_inches='tight')

