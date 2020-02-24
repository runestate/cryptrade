import sys; 
sys.path.append('../python')
sys.path.append('../generator')
from flask import Flask, jsonify, render_template
from matplotlib.finance import candlestick_ohlc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from applogging import Log
import numpy as np
from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig, StringExpert, version
from exp_moving_average_crossover_agent	import ExpMovingAverageCrossOverAgent
from moving_average_crossover_agent	import MovingAverageCrossOverAgent
from hodrick_prescott_feature import HodrickPrescottFeature
from candlestick_feature import CandlestickFeature
from passthrough_feature import PassthroughFeature
from stochastic_oscillator_agent import StochasticOscillatorAgent
from volume_agent import VolumeAgent
from generator_job import GeneratorJob
from feature_base import FeatureBase
from app import App
import os
import pandas as pd 
import matplotlib.pyplot as plt, mpld3
import random
from collections import namedtuple
import json
import time
from io import BytesIO 
import base64 
from zoom_size_plugin import ZoomSizePlugin
from numpy_encoder import NumpyEncoder
from json2html import json2html
from mpld3 import _display
_display.NumpyEncoder = NumpyEncoder
#
def dict_to_namedtuple(name, d):
	return namedtuple(name, d.keys())(*d.values())
style = dict_to_namedtuple('style', dict(
		backgroundColor='#272822',
		color='#cfcfc2'
	))
agents = [
	PassthroughFeature, 
	VolumeAgent,
	HodrickPrescottFeature, 
	CandlestickFeature,
	MovingAverageCrossOverAgent,
	ExpMovingAverageCrossOverAgent,
	StochasticOscillatorAgent
	]#.__name__: HodrickPrescottFeature
agent_map = { a.NAME: a for a in agents }

class PlotExert(App):
	agent_names = list(agent_map.keys())
	def __init__(self):
		super().__init__(__file__)
	def style_plot(self, fig, title):
		foreground_color = style.color
		background_color = style.backgroundColor
		fig.patch.set_alpha(0)
		for spine in fig.spines:
			fig.spines[spine].set_color(background_color)
		fig.tick_params(axis='x', colors=foreground_color)	
		fig.tick_params(axis='y', colors=foreground_color)
		fig.xaxis_date()
		for label in fig.xaxis.get_ticklabels(): #TODO: fix ordinal bug
			label.set_rotation(10)
			label.set_fontsize(20) 
		for label in fig.yaxis.get_ticklabels():
			label.set_fontsize(20) 
		fig.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
		fig.xaxis.set_major_locator(mticker.MaxNLocator(10)) #number of x labels we want, like so: 
		
		fig.yaxis.grid(linestyle='dotted', alpha=.4) 
		fig.xaxis.grid(linestyle='dotted', alpha=.2) 
		yl = fig.set_ylabel('Price', color=foreground_color, fontsize=26)
		fig.set_title(title, color=foreground_color, fontsize=26)
pe = PlotExert()
app = Flask(__name__)
 
@app.route("/")
@app.route("/list")
def list():
	dirpath = AppConfig.setting('GENERATOR_DATA_DIRPATH')
	files = [f for f in os.scandir(dirpath) if f.name.endswith('.h5')]
	return render_template('files.html', style=style, files=files)
def h5_to_plot(h5, from_epoch, to_epoch, filterInNth, agents, format_as_image):
	Log.d('============')
	Log.d(agents)
	agent_keys = [a for a in agents.split(',') if a]
	if len(agent_keys) == 0:		
		return 'No agent selected'
	filterInNth = int(filterInNth)
	df_info = ''
	pd.options.display.float_format = '{:.2f}'.format
	df_info += 'No agent selected\n\n{}\n\n'.format(h5.info())
	for key in h5:
		where = 'index >= {} and index <= {}'.format(from_epoch, to_epoch)
		Log.d('where: {}', where)
		frame = pd.read_hdf(h5, key, where=where)
		if frame.empty == True:
			return 'Empty frame'
		df_info += '{}\n\n'.format(frame.describe())
		background_color = '#272822'
		minute_intervals = [
			12 * 60,  # 12 hours
			] 
		x = range(100)
		y = [a * 2 + random.randint(-20, 20) for a in x]
		fig, ax = plt.subplots(figsize=(23,12))#figsize=(28,21))
		fig.patch.set_facecolor(background_color)			
		Log.t('building plot')
		is_image_format = int(format_as_image) == True
		def label_connect(path_collection, labels, color=None):
			tooltip = mpld3.plugins.PointHTMLTooltip(
				path_collection, 
				['<span class="point-tooltip" style="color: {}">{} <span class="point-tooltip-key">{}<span><span>'.format(color, l, key) for l in labels], 
				voffset=100, hoffset=0
				)
			mpld3.plugins.connect(fig, tooltip)
		for agent_key in agent_keys:
			try:
				agent_name = agent_key.split('(')[0]
				Log.d('plotting agent: {} -> {}', agent_key, agent_name)
				agent = agent_map[agent_name]
				plot_title = ''
				col_prefix = 'feature_{}_'.format(agent_key)
				agent_plot = agent.plot(
					plot_title, None, frame, ax,  is_image_format, 
					label_connect=label_connect, 
					filter_in_nth=filterInNth, 
					cp=col_prefix
					)
				pe.style_plot(ax, plot_title)
			except KeyError as ke:
				Log.w('Valid keys are: {}', frame.keys())
				raise ke
		plot_dirpath = AppConfig.setting('PLOT_DIRPATH')
		plot_filepath = os.path.join(plot_dirpath, '{}.png'.format('some plot'))
		
		fig.patch.set_facecolor(style.backgroundColor)			
		fig.tight_layout()
		if is_image_format == True:
			sio = BytesIO() 
			fig.savefig(sio, facecolor=fig.get_facecolor(), edgecolor='none', format="png") 
			html = '<img src="data:image/png;base64,{}"/>'.format(base64.encodebytes(sio.getvalue()).decode()) 
			return html
		mpld3.plugins.connect(fig, ZoomSizePlugin())
		return mpld3.fig_to_html(fig)
	raise 'hmmm'
 
@app.route("/frame/<filename>", defaults={
	'mode': 'html',
	'from_epoch': None, #int(time.time()) - 60*60*24*7, 
	'to_epoch': int(time.time()), 
	'filterInNth': 50,
	'agents': '',
	'format_as_image': '0'
	})
@app.route("/frame/<mode>/<filename>/<from_epoch>/<to_epoch>/<filterInNth>/<agents>/<format_as_image>")
def frame(mode, filename, from_epoch, to_epoch, filterInNth, agents, format_as_image):
	dirpath = AppConfig.setting('GENERATOR_DATA_DIRPATH')
	filepath = os.path.join(dirpath, filename)
	if from_epoch is None:
		from_epoch = to_epoch - 60*60*24*7
	with pd.HDFStore(filepath, mode='r') as h5:		
		key = h5.keys()[0] # TODO: always select first?
		storer = h5.get_storer(key)
		row_count = storer.nrows
		Log.d(row_count)
		first_epoch = pd.read_hdf(h5, key, start=0, stop=1, columns=[]).index.values[0]
		last_epoch = pd.read_hdf(h5, key, start=row_count-1, stop=row_count, columns=[]).index.values[0]
		column_names = [attr for attr in storer.attrs.data_columns]
		plot_html = h5_to_plot(h5, from_epoch, to_epoch, filterInNth, agents, format_as_image)
		if mode == 'plot_only':
			return plot_html
		feature_columns = set([a.split('_')[1] for a in column_names if a.startswith('feature_')])
		feature_names = [c.split('(')[0] for c in feature_columns]
		agent_map = { 
				fn:[
					c for c in feature_columns 
					if c.startswith(fn)
					] 
				for fn in feature_names  
			}
		return render_template(
			'frame.html', 
			style=style,
			plothtml=plot_html,
			filename=filename, 
			from_epoch=from_epoch, 
			to_epoch=to_epoch, 
			first_epoch=first_epoch,
			last_epoch=last_epoch,
			min_epoch=1514764800,
			max_epoch=int(time.time()),
			agent_map=sorted(agent_map.items()), # min epoch is 2018
			job_uid=key,
			frame_info_html=json2html.convert(json = { 'row count': row_count, 'columns': column_names })
			)
@app.route("/frame-info/<filename>")
def frame_info(filename):
	dirpath = AppConfig.setting('GENERATOR_DATA_DIRPATH')
	filepath = os.path.join(dirpath, filename)
	result = {}
	with pd.HDFStore(filepath, mode='r') as h5:		
		key = h5.keys()[0] # TODO: always select first?
		storer = h5.get_storer(key)
		time_column_names = [attr for attr in storer.attrs.data_columns if attr.endswith(')_time')]
		frame = pd.read_hdf(h5, key)#, columns=column_names)
		active_cols = [attr for attr in storer.attrs.data_columns if attr.endswith('_active')]
		row_count = len(frame)
		result[key] = {
			'row count': row_count,
			'time cols sum': json2html.convert(frame[time_column_names].sum().to_json()),
			'active_ratios': json2html.convert( ( frame[active_cols].sum() / row_count ).to_json()),
			'latest_row': json2html.convert( frame.iloc[-1].to_json() ),
			'isnull-sum': json2html.convert(frame.isnull().sum().to_json()),
			'describe': json2html.convert(frame.describe().to_json()),
			}
	return render_template(
		'frame-info.html', 
		style=style,
		frame_info_map=result
		)
