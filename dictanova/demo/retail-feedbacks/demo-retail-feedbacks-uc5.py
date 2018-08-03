# -*- coding: utf-8 -*-

"""
UC#05 : Perception per vendor, shop, customer segment...
Reveal the perception differences between vendors, shops, customer segments... 
"""

import pandas as pd
import requests, json
import numpy as np
import sys
import math
from wordcloud import WordCloud
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

if __name__ == "__main__":
	# Prepare Auth handler with API client id and secret
	# https://docs.dictanova.io/docs/authentication-and-security
	clientId, clientSecret = open("../credentials", "r").readline().strip().split(";")
	dictanova_auth = DictanovaAPIAuth(clientId, clientSecret)
	
	################################################### TOP OPINIONS PER VENDOR
	print("Computing top opinions per vendor")
	print("\tquery")
	query = {
		"type": "COUNT",
		"field": "externalId",
		"dimensions": [{
				"field": "metadata.vendor",
				"group": "DISTINCT",
				"limit": 9
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 15
			}
		]
	}
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
		json=query,
		auth=dictanova_auth)
	print("\t%s" % r)
	
	# Prepare data
	print("\tprepare data")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df = df[df["value"] > 0] # remove null
	df["vendor"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])

	# Build wordcloud per vendor
	print("\trender")
	vendors = list(df["vendor"].unique())
	row = math.ceil(math.sqrt(len(vendors)))
	col = math.floor(math.sqrt(len(vendors)))
	fig, axis = plt.subplots(row, col)
	fig.tight_layout()
	for i, vendor in enumerate(vendors):
		# Compute word distribution for wordcloud
		wc_freq = {row.opinion:row.value for row in df[df["vendor"]==vendor].itertuples()}
		wc = WordCloud(
			prefer_horizontal=1,
			background_color="white",
			colormap=colors.ListedColormap(colors=["darkblue"]) 
		)
		wc.fit_words(wc_freq)
		# Add to subfig
		r = i//col
		c = i%col
		axis[r][c].imshow(wc)
		axis[r][c].set_title(vendor)
		axis[r][c].axis("off")
	# plt.show()
	plt.savefig("uc5-top-opinions-per-vendor.png")
	plt.clf()
	
	################################################### TOP SPECIFIC OPINIONS PER VENDOR
	print("Computing top specific opinions per vendor")
	print("\tquery")
	query = {
		"type": "COUNT",
		"field": "externalId",
		"dimensions": [{
				"field": "metadata.vendor",
				"group": "DISTINCT",
				"limit": 9
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 100
			}
		]
	}
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
		json=query,
		auth=dictanova_auth)
	print("\t%s" % r)
	
	# Prepare data
	print("\tprepare data")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df = df[df["value"] > 0] # remove null
	df["vendor"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df.drop(columns=["dimensions", "volume"], inplace=True)
	df.set_index(["opinion", "vendor"], inplace=True)
	df_var = df.groupby(level="opinion").transform(lambda x: (x - x.mean())/x.std()) # normalize by mean and std
	df_var = df_var.unstack()
	df_var.columns = df_var.columns.droplevel(0) # simplify the data

	# Barchart per vendor
	for vendor in df_var.columns:
		print("\trender bc vendor '%s'" % vendor)
		# filter out data lower than 0 or NaN
		df_vendor = df_var[df_var[vendor]>0][vendor].sort_values(ascending=True, na_position="first")
		# top 15 most specific opinions
		df_vendor.iloc[-15:].plot.barh(
				title="Top opinions specific to '%s'" % vendor,
				colormap=colors.ListedColormap(colors=["C0"])
			)
		plt.savefig(
			"uc5-bc-top-specific-opinions-for-%s.png" % vendor,
			bbox_inches="tight"
		)
		plt.clf()

	# Build wordcloud per vendor
	wc = WordCloud(
			prefer_horizontal=1,
			background_color="white",
			colormap=colors.ListedColormap(colors=["C0"]) 
		)
	for vendor in df_var.columns:
		print("\trender wc vendor '%s'" % vendor)
		wc_freq = {k:v for k,v in df_var[vendor].items() if v>0}
		wc.fit_words(wc_freq)
		plt.imshow(wc)
		plt.title("Top opinions specific to '%s'" % vendor)
		plt.axis("off")
		# plt.show()
		plt.savefig(
			"uc5-wc-top-specific-opinions-for-%s.png" % vendor,
			bbox_inches="tight"
		)
		plt.clf()
	
	######################################## TOP SPECIFIC OPINIONS PER VENDOR WITH POLARITY
	print("Computing top specific opinions per vendor with polarity")
	print("\tquery")
	query = {
		"type": "COUNT",
		"field": "externalId",
		"dimensions": [{
				"field": "metadata.vendor",
				"group": "DISTINCT",
				"limit": 9
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 100
			}, {
				"field": "TERMS_POLARITY",
				"group": "DISTINCT"
			}
		]
	}
	r = requests.post(
		"https://api.dictanova.io/v1/aggregation/datasets/5b55b264dbcd8100019f0495/documents",
		json=query,
		auth=dictanova_auth)
	print("\t%s" % r)

	# Prepare data
	print("\tprepare data")
	df = pd.io.json.json_normalize(r.json()["periods"][0]["values"])
	df = df[df["value"] > 0] # remove null
	df["vendor"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df["polarity"] = df["dimensions"].apply(lambda x: x[2])
	# positive
	df_pos = df[df["polarity"]=="POSITIVE"][["opinion", "vendor", "value"]].set_index(["opinion", "vendor"])
	df_pos_var = df_pos.groupby(level="opinion").transform(lambda x: (x - x.mean())/x.std()) # normalize by mean and std
	df_pos_var = df_pos_var.unstack()
	df_pos_var.columns = df_pos_var.columns.droplevel(0) # simplify the data
	# negative
	df_neg = df[df["polarity"]=="NEGATIVE"][["opinion", "vendor", "value"]].set_index(["opinion", "vendor"])
	df_neg_var = df_neg.groupby(level="opinion").transform(lambda x: (x - x.mean())/x.std()) # normalize by mean and std
	df_neg_var = df_neg_var.unstack()
	df_neg_var.columns = df_neg_var.columns.droplevel(0) # simplify the data

	# Barchart per vendor
	for vendor in df_var.columns:
		print("\trender bc vendor '%s'" % vendor)
		# filter out data lower than 0 or NaN
		df_pos_vendor = df_pos_var[df_pos_var[vendor]>0][vendor].sort_values(ascending=True, na_position="first")
		df_neg_vendor = df_neg_var[df_neg_var[vendor]>0][vendor].sort_values(ascending=True, na_position="first")
		# top 15 most specific opinions
		fig, axis = plt.subplots(1, 2)
		axis[1].yaxis.tick_right()
		df_pos_vendor.iloc[-15:].plot.barh(
				ax=axis[1],
				title="Positive",
				colormap=colors.ListedColormap(colors=["seagreen"])
			)
		(df_neg_vendor.iloc[-15:]*-1).plot.barh( # negative just to make it nice, no meaning
				ax=axis[0],
				title="Negative",
				colormap=colors.ListedColormap(colors=["orangered"])
			)
		t = plt.suptitle("Top positive / negative opinions specific to '%s'" % vendor)
		axis[0].set_ylabel("")
		axis[1].set_ylabel("")
		xartists = [t] + axis[0].yaxis.get_majorticklabels() + axis[1].yaxis.get_majorticklabels()
		plt.savefig(
			"uc5-bc-top-specific-polarized-opinions-for-%s.png" % vendor,
			bbox_extra_artists=xartists, # help computation of right margins
			bbox_inches='tight'
		)
		plt.clf()