# Use the official Python base image
FROM python:3.8.10

# Set the working directory in the container
WORKDIR /data

# Copy your test data into the image
COPY T1GRS_test_data.vcf /data/T1GRS_test_data.vcf
COPY T1GRS_allele_order.txt /data/T1GRS_allele_order.txt
COPY ALL5_199_TOPMED_SUSIE_HLA_T1D_signals_updateID_r3.vcf.alleles /data/ALL5_199_TOPMED_SUSIE_HLA_T1D_signals_updateID_r3.vcf.alleles
COPY ALL5_199_TOPMED_SUSIE_HLA_T1D_signals_updateID.vcf.alleles /data/ALL5_199_TOPMED_SUSIE_HLA_T1D_signals_updateID.vcf.alleles
COPY ALL_NoPCs_Final.ubj /data/ALL_NoPCs_Final.ubj
COPY NOHLA_NoPCs_Final.ubj /data/NOHLA_NoPCs_Final.ubj
COPY HLA_ONLY_NoPCs_Final.ubj /data/HLA_ONLY_NoPCs_Final.ubj
COPY ALL_columns.txt /data/ALL_columns.txt
COPY HLA_columns.txt /data/HLA_columns.txt
COPY nonHLA_columns.txt /data/nonHLA_columns.txt
COPY T1GRS_total_percentile_risk.txt /data/T1GRS_total_percentile_risk.txt
COPY T1GRS_MHC_percentile_risk.txt /data/T1GRS_MHC_percentile_risk.txt
COPY T1GRS_nonMHC_percentile_risk.txt /data/T1GRS_nonMHC_percentile_risk.txt

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Command to run the script
ENTRYPOINT ["python", "./T1GRS_pipeline_R3.py"]
