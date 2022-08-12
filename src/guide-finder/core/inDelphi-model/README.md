# inDelphi-model

## Dependencies
- python 2.7+ or 3.4+
- pandas 0.23.4
- scikit-learn 0.18.1 or 0.20.0
- scipy 1.1.0
- numpy 1.15.3

The online interactive web app version of inDelphi uses the scikit-learn v0.18.1 models.


## Installation
Clone this github repository, then set up your environment to import the inDelphi.py script in however is most convenient for you. In python, for instance, you may use the following at the top of your script to import inDelphi.

```python
import sys
sys.path.append('/directory/to/local/indelphi/repo/clone/')
import inDelphi
```

## Usage
In python2.7+ or python3.4+:

```python
import inDelphi
inDelphi.init_model(celltype = 'mESC')
```

Note: Supported cell types are `['mESC', 'U2OS', 'HEK293', 'HCT116', 'K562']`. If your cell type of interest is not included here, we recommend using mESC if your cell type does not have known DNA repair defects and is not a cancer cell type. See www.crisprindelphi.design/guide for more details.

```python
pred_df, stats = inDelphi.predict(seq, cutsite)
```

`seq` is a string of DNA characters. `cutsite` is an int that specifies the 0-index position of the cutsite, such that `seq[:cutsite]` and `seq[cutsite:]` in Python notation describe the cut products.

`pred_df` is a pandas dataframe containing a row for each prediction. By default, a single prediction corresponds to a single genotype for 1-bp insertions and microhomology deletions. For microhomology-less deletions, a single prediction corresponds to a single predicted frequency for the sum total frequency of a group of microhomology-less deletions. Microhomology-less deletions are grouped by deletion length.
- 1-bp insertion genotypes are uniquely identified by `row['Category'] == 'ins'` and `row['Inserted Bases'].isin([A, C, G, T])`. 
- Microhomology deletions are uniquely identified by `row['Category'] == 'del'`, `1 <= row['Length'] <= 60`, and `0 <= row['Genotype position'] <= row['Length']`.
- Microhomology-less deletions are uniquely identified by `row['Category'] == 'del'`, `1 <= row['Length'] <= 60`, and `row['Genotype position'] == 'e'`.
- The column 'Predicted frequency' sums to 100.0.

`stats` is a dict with the following keys. For further details, refer to www.crisprindelphi.design/guide#batch4.
- Phi (Note: natural log of phi refers to microhomology strength)
- Precision
- 1-bp ins frequency
- MH del frequency
- MHless del frequency
- Frameshift frequency
- Frame +0 frequency
- Frame +1 frequency
- Frame +2 frequency
- Highest outcome frequency
- Highest del frequency
- Highest ins frequency
- Expected indel length
- Reference sequence
- Cutsite
- gRNA
- gRNA orientation
- Cas9 type
- Celltype

### Example usage
```python
import inDelphi
inDelphi.init_model(celltype = 'mESC')

left_seq = 'AGAATCGCCCGCGGTCCATCCTTTATCAGCGGGAATTCAAGCGCACCAGCCAGAGGTGTA'
right_seq = 'CCGTGGACGTGAGAAAGAAGAAACATAATATTCGCACTAGATCCATCCCCATACCTGACC'
seq = left_seq + right_seq
cutsite = len(left_seq)

pred_df, stats = inDelphi.predict(seq, cutsite)
```

## Additional methods
Once you have obtained `pred_df, stats`, additional methods are available for your convenience.

### Obtaining exact genotypes
```python
pred_df, stats = inDelphi.predict(seq, cutsite)
pred_df = inDelphi.add_genotype_column(pred_df, stats)
```

A new column `Genotype` will be created.
- If MH-less genotypes are represented with `pred_df['Genotype position'] == 'e'`, MH-less genotypes will not have a value for `Genotype` since these rows represent the total predicted frequency for a group of MH-less genotypes.

### Expanding microhomology-less deletion predictions into genotype resolution
Warning: Microhomology-less deletions are less consistent between experimental replicates than 1-bp insertions and microhomology deletions. inDelphi as presented in our manuscript was tested for performance only on grouped predictions for MH-less genotypes.

```python
pred_df, stats = inDelphi.predict(seq, cutsite)
pred_df = inDelphi.add_mhless_genotypes(pred_df, stats)
# pred_df = inDelphi.add_genotype_column(pred_df, stats) 
```

Microhomology-less deletions will be converted into a different representation:
- Microhomology-less deletions will be uniquely identified by `row['Category'] == 'del'`, `1 <= row['Length'] <= 60`, and `0 <= row['Genotype position'] <= row['Length']`.
- Microhomology-less deletions will no longer contain the value 'e' in 'Genotype position'
- The number of rows in `pred_df` will increase

For details on how predicted frequencies are converted, refer to https://www.crisprindelphi.design/guide#single4.

## Contact
maxwshen at mit.edu

### License
Limited Copyright License for Research Use by Non-Profit and Government Institutions

BY DOWNLOADING THE CODE OR USING THE SERVICE AND/OR SOFTWARE APPLICATION ACCOMPANYING THIS LICENSE, YOU ARE CONSENTING TO BE BOUND BY ALL OF THE TERMS OF THIS LICENSE

“Copyright 2018. Massachusetts Institute of Technology, The Broad Institute, Harvard University and Brigham and Women's Hospital. All Rights Reserved.”

The software is being provided as a service for research, educational, instructional and non-commercial purposes only. By generating a user account and/or submitting jobs to InDelphi you agree to the terms and conditions herein. You are an actively enrolled student, post-doctoral researcher, or faculty member at a degree-granting educational institution or US government research institution; and You will only use the InDelphi Software Application and/or Service for educational, instructional, and/or non-commercial research purposes; You understand that all results produced using the Code may only be used for non-commercial research and/or academic purposes; You understand that to obtain any right to use the Code for commercial purposes, or in the context of industrially sponsored research, You must enter into an appropriate, separate and direct license agreement with the Owners. You will not redistribute unmodified versions of the Code; You will redistribute modifications, if any, under the same terms as this license and only to non-profits and US government institutions; You must credit the authors of the Code: David K. Gifford, Jonathan Yee-Ting Hsu and Max Walt Shen and cite Predictable and precise template-free editing of pathogenic mutations by CRISPR-Cas9 nuclease", Nature, 2018,  doi:10.1038/s41586-018-0686-x; and You understand that neither the names of the Owners nor the names of the authors may be used to endorse or promote products derived from this software without specific prior written permission.
