# -*- coding: utf-8 -*-

"""
UC#06: Evolution over time
How opinions evolve over time?
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
	
	################################################# OPINIONS COUNT OVER TIME
	print("Volume of opinions over time")
	print("\tquery")
	query = {
		"type": "COUNT",
		"field": "externalId",
		"periods": [
			{
				"field": "metadata.date_of_purchase",
				"from": "2015-01-01T00:00:00Z",
				"to": "2015-12-31T23:59:59Z"
			}
		],
		"dimensions" : [
			{
				"field": "metadata.date_of_purchase",
				"group": "MONTH"
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
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
	df["month"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df = df.pivot_table(index="month", columns="opinion", values="volume")
	df.fillna(0, inplace=True) # approx

	# Plot top 5 over period
	print("\trender")
	df.plot.line(
		y=df.sum().sort_values(ascending=False).iloc[:5].index,
		title="Volume of top opinions over time",
	)
	plt.savefig(
		"uc6-evolution-volume-opinions.png",
		bbox_inches="tight"
	)
	plt.clf()

	######################################## OPINIONS COUNT OVER TIME WITH POLARITY
	print("Volume of opinions over time with polarity")
	print("\tquery")
	query = {
		"type": "COUNT",
		"field": "externalId",
		"periods": [
			{
				"field": "metadata.date_of_purchase",
				"from": "2015-01-01T00:00:00Z",
				"to": "2015-12-31T23:59:59Z"
			}
		],
		"dimensions" : [
			{
				"field": "metadata.date_of_purchase",
				"group": "MONTH"
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 10
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
	df["month"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df["polarity"] = df["dimensions"].apply(lambda x: x[2])
	df.fillna(0, inplace=True) # approx
	df = df.pivot_table(index=["opinion", "month"], columns="polarity", values="volume")
	df["POS_PERC"] = 100. * df["POSITIVE"] / df.sum(axis="columns")
	df["NEG_PERC"] = 100. * df["NEGATIVE"] / df.sum(axis="columns")
	df["NEU_PERC"] = 100. * df["NEUTRAL"] / df.sum(axis="columns")

	# Plot
	for opinion in df.index.levels[0]:
		print("\trender volume '%s'" % opinion)
		df.loc[opinion][["POSITIVE","NEGATIVE","NEUTRAL"]].plot.line(
			title="Volume of '%s' per polarity over time" % opinion,
			colormap=colors.ListedColormap(["seagreen", "orangered", "darkgrey"])
		)
		plt.savefig(
			"uc6-evolution-volume-with-polarity-%s.png" % opinion,
			bbox_inches="tight"
		)
		plt.clf()
		print("\trender proportions '%s'" % opinion)
		df.loc[opinion][["POS_PERC","NEG_PERC","NEU_PERC"]].plot.line(
			title="Proporition of polarity for '%s' over time" % opinion,
			colormap=colors.ListedColormap(["seagreen", "orangered", "darkgrey"])
		)
		plt.savefig(
			"uc6-evolution-proportion-of-polarity-%s.png" % opinion,
			bbox_inches="tight"
		)
		plt.clf()

	######################################## NPS EVOLUTION PER OPINION
	print("NPS per opinion over time")
	print("\tquery")
	query = {
		"type": "NPS",
		"field": "metadata.rating_nps",
		"periods": [
			{
				"field": "metadata.date_of_purchase",
				"from": "2015-01-01T00:00:00Z",
				"to": "2015-12-31T23:59:59Z"
			}
		],
		"dimensions" : [
			{
				"field": "metadata.date_of_purchase",
				"group": "MONTH"
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 5
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
	df["month"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df.set_index(["opinion", "month"], inplace=True)
	df.rename(columns={"value": "NPS"}, inplace=True)
	df.drop(columns=["dimensions"], inplace=True)

	# Plot over period
	for opinion in df.index.levels[0]:
		print("\trender '%s'" % opinion)
		df.loc[opinion].plot.line(
			title="NPS of '%s' over time" % opinion,
			subplots=True
		)
		plt.savefig(
			"uc6-evolution-nps-%s.png" % opinion,
			bbox_inches="tight"
		)
		plt.clf()
	
	################################# NPS EVOLUTION PER OPINION WITH POLARITY
	print("NPS per opinion over time with polarity")
	print("\tquery")
	query = {
		"type": "NPS",
		"field": "metadata.rating_nps",
		"periods": [
			{
				"field": "metadata.date_of_purchase",
				"from": "2015-01-01T00:00:00Z",
				"to": "2015-12-31T23:59:59Z"
			}
		],
		"dimensions" : [
			{
				"field": "metadata.date_of_purchase",
				"group": "MONTH"
			}, {
				"field": "TERMS",
				"group": "DISTINCT",
				"limit": 5
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
	df["month"] = df["dimensions"].apply(lambda x: x[0])
	df["opinion"] = df["dimensions"].apply(lambda x: x[1])
	df["polarity"] = df["dimensions"].apply(lambda x: x[2])
	df = df.pivot_table(index=["opinion", "month"], columns="polarity", values="value")

	# Plot over period
	for opinion in df.index.levels[0]:
		print("\trender '%s'" % opinion)
		df.loc[opinion][["POSITIVE","NEGATIVE"]].plot.line(
			title="NPS of '%s' over time" % opinion,
			subplots=True,
			ylim=(-100, 100),
			colormap=colors.ListedColormap(["seagreen", "orangered"])
		)
		plt.savefig(
			"uc6-evolution-nps-%s-polarized.png" % opinion,
			bbox_inches="tight"
		)
		plt.clf()
