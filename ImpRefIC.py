#!/usr/bin/python
#coding:utf-8
import re
import sys
import numpy as np
import pandas as pd
import bz2
import gzip
import time
from time import strftime, gmtime
from collections import defaultdict
import joblib
import metrics
from sklearn.metrics import *
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import warnings
warnings.filterwarnings("ignore")

start_time = time.time()

input_file = sys.argv[1] #target VCF file
ImpRef_path = sys.argv[2] #software path
out_path = sys.argv[3] #output file path

#Corresponding markers in the reference and target files must have identical CHROM, POS, REF, and ALT fields
all_SNP = {}
consistent_SNP = defaultdict(list)
with bz2.open(ImpRef_path + "/SNP.INFO.bz2",'rt') as file1:
    for line in file1:
        line_list = line.strip().split()
        all_SNP.update({line_list[0]+','+line_list[1]+','+line_list[2]+','+line_list[3]:line})
with gzip.open(input_file,'rt') as file2:
    for line in file2:
        if line.startswith("#"):
            pass
        else:
            line_list = line.strip().split()
            lines = line_list[0]+','+line_list[1]+','+line_list[3]+','+line_list[4]
            if lines in all_SNP:
                consistent_SNP[lines].append(all_SNP[lines])

#Target VCF file
study_sample = []
base = {'A': 0, 'T': 0.1, 'C': 0.3, 'G':0.7, 'N':0.9}
study_geno = {}
SNP_num = 0
with gzip.open(input_file, 'rt') as file3:
    for line in file3:
        if line.startswith("##"):
            pass
        if line.startswith("#"):
            line_list = line.strip('\n').split('\t')
            study_sample.extend(line_list[i] for i in range(9, len(line_list)))
            continue
        SNP_num = SNP_num + 1
        var = line.strip('\n').split('\t', 6)[:5]
        if var[0]+","+var[1]+","+var[3]+","+var[4] in consistent_SNP:
            var = line.strip('\n').split('\t')
            allele = [var[3], var[4]]
            for i in range(9, len(var)):
                if var[i].startswith('./.'):
                    var[i] = base['N']+base['N']
                else:
                    var[i] = round((base[allele[int(re.split(r'[\|\/]', var[i])[0])]] + base[allele[int(re.split(r'[\|\/]', var[i])[1])]]),1)
            study_geno[var[0]+","+var[1]+","+var[3]+","+var[4]] = var[9:]

print("[INFO] Study samples: "+ str(len(study_sample)))
print("[INFO] Study snps: "+ str(SNP_num))
print("[INFO] Consistent snps: "+ str(len(consistent_SNP)) + "\n")

study_G = np.concatenate([[study_geno[i]] for i in consistent_SNP],axis=0)
study_G = study_G.T

#Reference file as model training set
ref_geno={}
with open(ImpRef_path + "/chr1-18.pos_snp_sample.matrix",'rt') as file4:
    for line in file4:
        line_list = line.strip().split()
        lines = (',').join(line_list[:4])
        if lines in consistent_SNP:
            ref_geno[lines] = line_list[4:]
ref_G = np.concatenate([[ref_geno[i]] for i in consistent_SNP],axis=0)

x = ref_G.T

#Label
ref_class = []
F = open(ImpRef_path + "/ref_class.txt",'rt')
for line in F:
    line=line.strip('\n')
    ref_class.append(int(line))

y = np.array(ref_class)

#Upsampling
from imblearn.over_sampling import RandomOverSampler
ros = RandomOverSampler(random_state=0)
x_resampled, y_resampled = ros.fit_resample(x, y)

#Model Initialization
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(multi_class="multinomial", solver="lbfgs", C=10, max_iter=1000, n_jobs=-1)

#Model Evaluation Metrics
def get_metrics(y_test, y_predicted):
    Accuracy = accuracy_score(y_test, y_predicted)
    Precision = precision_score(y_test, y_predicted, average='weighted')
    Recall = recall_score(y_test, y_predicted, average='weighted')
    F1 = f1_score(y_test, y_predicted, average='weighted')
    return Accuracy, Precision, Recall, F1

#Divide training set and test set
x_train, x_test, y_train, y_test = train_test_split(x_resampled, y_resampled, test_size = 0.20, random_state=None)
print("[INFO] Successfully initialize a new model !")

#Model training
print("[INFO] Training the model …… ")
model.fit(x_train,y_train)
print("[INFO] Model training completed !\n")

#The trained model predicts the test set
y_pred=model.predict(x_test)
print("===================Confusion Matrix===================")
print(pd.crosstab(pd.Series(y_test, name='Actual'), pd.Series(y_pred, name='Predicted')))
Accuracy, Precision, Recall, F1 = get_metrics(y_test, y_pred)
print("Accuracy = %.4f \nPrecision = %.4f \nRecall = %.4f \nF1 = %.4f" % (Accuracy, Precision, Recall, F1))

#Save model
joblib.dump(model, out_path + "/LogisticRegression.pkl")
print("[INFO] Model has been saved to" + out_path + "/LogisticRegression.pkl")

#The trained model predicts the target file
print("[INFO] The model starts predicting the target file …… ")
w_proba = model.predict_proba(study_G)
w = model.predict(study_G)

#Output predicted probabilities and optimal reference population
population = np.array([["American_Yorkshire"],["Canadian_Yorkshire"],["Danish_Yorkshire"],["Dutch_Yorkshire"],["French_Yorkshire"],["Unknown_Yorkshire_lines"],["Landrace"],["Duroc"],["Berkshire"],["Goettingen_Minipig"],["Hampshire"],["Iberian"],["Mangalica"],["Pietrain"],["Angler_Sattleschwein"],["British_Saddleback"],["Bunte_Bentheimer"],["Calabrese"],["Casertana"],["Chato_Murciano"],["Cinta_Senese"],["Gloucester_Old_Spot"],["Large_Black"],["Leicoma"],["Linderodsvin"],["Middle_White"],["Nero_Siciliano"],["Tamworth"],["European_Wild_boar"],["Yucatan_minipig"],["Creole"],["American_Wild_boar"],["Bamei"],["Baoshan"],["Enshi_black"],["Erhualian"],["Hetao"],["Jinhua"],["Korean_black_pig"],["Laiwu"],["Meishan"],["Min"],["Neijiang"],["Rongchang"],["Tibetan"],["Tongcheng"],["Hubei_White"],["Daweizi"],["Jiangquhai"],["Leping_Spotted"],["Penzhou"],["songliao_black_pig"],["Taihu"],["Wannan_Spotted"],["Wujin"],["Ya_nan"],["Diannanxiaoer"],["Luchuan"],["Wuzhishan"],["Bamaxiang"],["MiniLEWE"],["Xiang"],["Asia_Wild_boar"],["Hybrid"]])
study_sample = np.array(study_sample).reshape(len(study_sample),1)
out_population = np.append(study_sample, population[w], axis=1)
np.savetxt(out_path + "/ImpRef.out.population", out_population, fmt='%s', delimiter='\t')
np.savetxt(out_path + "/ImpRef.out.ref.population", np.unique(population[w]), fmt='%s', delimiter='\t')
np.savetxt(out_path + "/ImpRef.out.population.proba", population[np.unique(y)].transpose(), fmt='%s', delimiter='\t')
f = open(out_path + "/ImpRef.out.population.proba", "ab")
np.savetxt(f, w_proba, fmt='%.4f', delimiter='\t')

#Total running time
end_time = time.time()
run_time = end_time - start_time
run_time = strftime("%H:%M:%S", gmtime(run_time))

print("[INFO] Prediction complete ! The predicted frequencies and predicted optimal reference population have been saved to " + out_path)
print("[INFO] Total time consumption is ",run_time)