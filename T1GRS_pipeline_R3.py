import numpy as np
import pandas as pd
import xgboost as xgb
import gzip
from io import StringIO
import argparse

def read_vcf(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if not line.startswith('##')]
    file_content = StringIO('\n'.join(lines))
    df = pd.read_csv(file_content, sep='\t')
    return df

def main(args):
    vcf_df = read_vcf(args.vcf_path)
    
    R3_Variants_to_keep = pd.read_csv(args.r3_variants_path, sep='\t', names=['#CHROM', 'POS', 'ID', 'REF', 'ALT'])
    vcf_filt = pd.merge(vcf_df, R3_Variants_to_keep, on=['#CHROM', 'POS', 'ID', 'REF', 'ALT'])
    vcf_filt.rename(columns={'ID': 'rsid'}, inplace=True)

    R2_snps_allele_order = pd.read_csv(args.r2_snps_path, sep='\t')
    R2_snps = R2_snps_allele_order[['ID', 'rsid']]
    vcf_filt_R2 = pd.merge(R2_snps, vcf_filt, on=['rsid'])

    T1df = vcf_filt_R2.copy(deep=True)
    T1df.index = T1df["ID"]
    T1df = T1df.drop(["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", "rsid"], axis=1)
    T1df.columns = [x.split("_", 1)[1] for x in T1df.columns]
    T1df = np.transpose(T1df)

    cols2map_all = [x for x in T1df.columns if 'chr' in x or 'rs' in x or '_' in x]
    for col in cols2map_all:
        T1df[col] = T1df[col].map({"0|0": 0, "0|1": 1, "1|0": 1, "1|1": 2, "0/0": 0, "0/1": 1, "1/0": 1, "1/1": 2})

    allele_order = pd.read_csv(args.allele_order_path, sep=' ', names=['ID', 'REF_true', 'ALT_true'])
    merged_allele_order = pd.merge(allele_order, vcf_filt_R2, on=['ID'])
    merged_allele_order_flip = merged_allele_order.loc[~(merged_allele_order['ALT_true'] == merged_allele_order['ALT'])]
    cols_to_flip = merged_allele_order_flip.ID.to_list()
    for column in cols_to_flip:
        T1df[column] = T1df[column].map({0: 2, 1: 1, 2: 0})

    xgb_ALL = xgb.XGBClassifier()
    xgb_ALL.load_model(args.xgb_all_model_path)

    xgb_NOHLA = xgb.XGBClassifier()
    xgb_NOHLA.load_model(args.xgb_nohla_model_path)

    xgb_HLAONLY = xgb.XGBClassifier()
    xgb_HLAONLY.load_model(args.xgb_hlaonly_model_path)

    ALL_columns = list(pd.read_csv(args.all_columns_path, sep='\t', header=None, index_col=0)[1])
    HLA_columns = list(pd.read_csv(args.hla_columns_path, sep='\t', header=None, index_col=0)[1])
    nonHLA_columns = list(pd.read_csv(args.nonhla_columns_path, sep='\t', header=None, index_col=0)[1])

    T1D_ALL = T1df[ALL_columns]
    T1D_HLA = T1df[HLA_columns]
    T1D_nonHLA = T1df[nonHLA_columns]

    ALL_test = list(xgb_ALL.predict_proba(T1D_ALL)[:, 1])
    HLA_test = list(xgb_HLAONLY.predict_proba(T1D_HLA)[:, 1])
    nonHLA_test = list(xgb_NOHLA.predict_proba(T1D_nonHLA)[:, 1])

    T1D_IDs = T1D_ALL.index.to_list()
    all_lists = [T1D_IDs, ALL_test, HLA_test, nonHLA_test]
    T1GRS_probabilities = pd.DataFrame(all_lists).T
    T1GRS_probabilities.columns = ['ID', 'T1GRS_ALL', 'T1GRS_MHC', 'T1GRS_nonMHC']

    def calculate_percentiles(probabilities, percentiles_path, column_name):
        percentiles_data = pd.read_csv(percentiles_path, sep='\t')
        percentiles = []
        for value in probabilities:
            percentile = percentiles_data.loc[(percentiles_data.iloc[:, 0] - value).abs().idxmin()][1]
            percentiles.append(percentile)
        return percentiles

    T1GRS_probabilities['Probability ALL percentile'] = calculate_percentiles(T1GRS_probabilities['T1GRS_ALL'].to_list(), args.total_percentiles_path, 'Probability_Total_num')
    T1GRS_probabilities['Probability MHC percentile'] = calculate_percentiles(T1GRS_probabilities['T1GRS_MHC'].to_list(), args.mhc_percentiles_path, 'Probability_MHC_num')
    T1GRS_probabilities['Probability nonMHC percentile'] = calculate_percentiles(T1GRS_probabilities['T1GRS_nonMHC'].to_list(), args.nonmhc_percentiles_path, 'Probability_nonMHC_num')

    T1GRS_probabilities.to_csv(args.output_path, index=False)
    print(f"Results saved to {args.output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process input and output file paths.')
    parser.add_argument('--vcf_path', required=True, help='Path to the VCF file')
    parser.add_argument('--r3_variants_path', required=True, help='Path to the R3 variants file')
    parser.add_argument('--r2_snps_path', required=True, help='Path to the R2 SNPs file')
    parser.add_argument('--allele_order_path', required=True, help='Path to the allele order file')
    parser.add_argument('--xgb_all_model_path', required=True, help='Path to the XGBoost ALL model file')
    parser.add_argument('--xgb_nohla_model_path', required=True, help='Path to the XGBoost NOHLA model file')
    parser.add_argument('--xgb_hlaonly_model_path', required=True, help='Path to the XGBoost HLAONLY model file')
    parser.add_argument('--all_columns_path', required=True, help='Path to the ALL columns file')
    parser.add_argument('--hla_columns_path', required=True, help='Path to the HLA columns file')
    parser.add_argument('--nonhla_columns_path', required=True, help='Path to the nonHLA columns file')
    parser.add_argument('--total_percentiles_path', required=True, help='Path to the total percentiles file')
    parser.add_argument('--mhc_percentiles_path', required=True, help='Path to the MHC percentiles file')
    parser.add_argument('--nonmhc_percentiles_path', required=True, help='Path to the nonMHC percentiles file')
    parser.add_argument('--output_path', required=True, help='Path to the output file')
    
    args = parser.parse_args()
    main(args)
