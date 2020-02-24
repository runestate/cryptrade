from numpy import nan, float64
import pandas as pd
import numpy as np
from predictor_base import PredictorBase
from applogging import Log
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier, ExtraTreesClassifier, VotingClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, cross_val_score, StratifiedKFold, learning_curve
from sklearn.model_selection import train_test_split
from datetime import datetime
import multiprocessing
core_count = multiprocessing.cpu_count()
sns.set(style='white', context='notebook', palette='deep')

class EnsemblePredictor(PredictorBase):
	name = 'ensmbl'
	prefix = 'prediction_ensmbl_next_trend_feature'
	def __init__(self, min_predict_generator_size, max_train_size):
		super().__init__(predict_col='feature_rtrspc()_next_trend_pricefeature')
		assert max_train_size > min_predict_generator_size
		self.min_predict_generator_size = min_predict_generator_size 
		self.max_train_size = max_train_size
		self.predictor = None
		Log.d('core count: {}', core_count)
	def process(self, epoch, df):
		if df.empty:
			return
		if self.predictor is not None:
			return this.predictor.predict(...)
		r_index = df.index.get_loc(epoch)	
		not_enough_predictor_data = r_index +1 < self.min_predict_generator_size 
		if not_enough_predictor_data:
			return
		self.__create_predictor(df)
		return
	def __create_predictor(self, df):
		Log.i('creating predictor on {} rows', len(df))
		assert not df.empty
		kfold = StratifiedKFold(n_splits=10)
		random_state = 2
		classifiers = []
		classifiers.append(SVC(random_state=random_state))
		classifiers.append(DecisionTreeClassifier(random_state=random_state))
		classifiers.append(AdaBoostClassifier(DecisionTreeClassifier(random_state=random_state),random_state=random_state,learning_rate=0.1))
		classifiers.append(RandomForestClassifier(random_state=random_state))
		classifiers.append(ExtraTreesClassifier(random_state=random_state))
		classifiers.append(GradientBoostingClassifier(random_state=random_state))
		classifiers.append(MLPClassifier(random_state=random_state))
		classifiers.append(KNeighborsClassifier())
		classifiers.append(LogisticRegression(random_state = random_state))
		classifiers.append(LinearDiscriminantAnalysis())
		X_all, y_all = self.frame_to_ml_inputs(df, do_filter=True, max_train_size=self.max_train_size)
		if X_all.empty:
			Log.w('could not create predictor as the preprocessing resulted in an empty dataframe')
			return
		X_train, X_test, Y_train, Y_test = train_test_split(X_all, y_all, test_size=0.2, random_state=random_state)
		Log.d('train shape: X: {}, y: {}', X_train.shape, Y_train.shape)
		cv_results = []
		for classifier in classifiers :
			Log.d('performing cross val score for predictor {}', classifier)
			start_time = datetime.now()
			cv_results.append(
				cross_val_score(classifier, X_train, y = Y_train, scoring = 'accuracy', cv = kfold, n_jobs=core_count)
			)
			Log.d('..done, time spent: {}', datetime.now() - start_time)
		cv_means = []
		cv_std = []
		for cv_result in cv_results:
			cv_means.append(cv_result.mean())
			cv_std.append(cv_result.std())
		cv_res = pd.DataFrame({
			'CrossValMeans': cv_means,
			'CrossValerrors': cv_std,
			'Algorithm': [
				'SVC',
				'DecisionTree',
				'AdaBoost',
				'RandomForest',
				'ExtraTrees',
				'GradientBoosting',
				'MultipleLayerPerceptron',
				'KNeighboors',
				'LogisticRegression',
				'LinearDiscriminantAnalysis'
				]})
		Log.d('cross val results:\n{}', cv_res)
		g = sns.barplot('CrossValMeans','Algorithm',data = cv_res, palette='Set3',orient = 'h',**{'xerr':cv_std})
		g.set_xlabel('Mean Accuracy')
		g = g.set_title('Cross validation scores')
		Log.i('saving plot..')
		plt.savefig('!eb1_cross_val_score.png', edgecolor='none', format="png") 
		DTC = DecisionTreeClassifier()
		adaDTC = AdaBoostClassifier(DTC, random_state=7)
		ada_param_grid = {'base_estimator__criterion' : ['gini', 'entropy'],
					  'base_estimator__splitter' :   ['best', 'random'],
					  'algorithm' : ['SAMME','SAMME.R'],
					  'n_estimators' :[1,2],
					  'learning_rate':  [0.0001, 0.001, 0.01, 0.1, 0.2, 0.3,1.5]}
		gsadaDTC = GridSearchCV(adaDTC,param_grid = ada_param_grid, cv=kfold, scoring='accuracy', n_jobs=core_count, verbose = 1)
		gsadaDTC.fit(X_train,Y_train)
		ada_best = gsadaDTC.best_estimator_
		gsadaDTC.best_score_
		ExtC = ExtraTreesClassifier()
		ex_param_grid = {'max_depth': [None],
					  'max_features': [1, 3, 10],
					  'min_samples_split': [2, 3, 10],
					  'min_samples_leaf': [1, 3, 10],
					  'bootstrap': [False],
					  'n_estimators' :[100,300],
					  'criterion': ['gini']}
		gsExtC = GridSearchCV(ExtC,param_grid = ex_param_grid, cv=kfold, scoring='accuracy', n_jobs=core_count, verbose = 1)
		gsExtC.fit(X_train,Y_train)
		ExtC_best = gsExtC.best_estimator_
		Log.d('gsExtC.best_score_: {}', gsExtC.best_score_)
		RFC = RandomForestClassifier()
		rf_param_grid = {'max_depth': [None],
					  'max_features': [1, 3, 10],
					  'min_samples_split': [2, 3, 10],
					  'min_samples_leaf': [1, 3, 10],
					  'bootstrap': [False],
					  'n_estimators' :[100,300],
					  'criterion': ['gini']}
		gsRFC = GridSearchCV(RFC,param_grid = rf_param_grid, cv=kfold, scoring='accuracy', n_jobs=core_count, verbose = 1)
		gsRFC.fit(X_train,Y_train)
		RFC_best = gsRFC.best_estimator_
		Log.d('gsRFC.best_score_: {}', gsRFC.best_score_)
		GBC = GradientBoostingClassifier()
		gb_param_grid = {'loss' : ['deviance'],
					  'n_estimators' : [100,200,300],
					  'learning_rate': [0.1, 0.05, 0.01],
					  'max_depth': [4, 8],
					  'min_samples_leaf': [100,150],
					  'max_features': [0.3, 0.1] 
					  }
		gsGBC = GridSearchCV(GBC,param_grid = gb_param_grid, cv=kfold, scoring='accuracy', n_jobs=core_count, verbose = 1)
		gsGBC.fit(X_train,Y_train)
		GBC_best = gsGBC.best_estimator_
		Log.d('gsGBC.best_score_: {}', gsGBC.best_score_)
		SVMC = SVC(probability=True)
		svc_param_grid = {'kernel': ['rbf'], 
						  'gamma': [ 0.001, 0.01, 0.1, 1],
						  'C': [1, 10, 50, 100,200,300, 1000]}
		gsSVMC = GridSearchCV(SVMC,param_grid = svc_param_grid, cv=kfold, scoring='accuracy', n_jobs=core_count, verbose = 1)
		gsSVMC.fit(X_train,Y_train)
		SVMC_best = gsSVMC.best_estimator_
		Log.d('gsSVMC.best_score_: {}', gsSVMC.best_score_)
		Log.w('quitting')
		exit()
