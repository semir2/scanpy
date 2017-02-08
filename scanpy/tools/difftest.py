# Copyright 2016-2017 F. Alexander Wolf (http://falexwolf.de).
"""
Differential Gene Expression Analysis

This is a Beta Version of a tool for differential gene expression testing
between sets detected in previous tools. Tools such as dpt, cluster,...
"""   

from itertools import combinations
import numpy as np
from scipy.stats.distributions import norm
from .. import utils
from .. import plotting as plott
from .. import settings as sett

def difftest(dgroups, adata=None,
             smp='groups',
             names='all',
             sig_level=0.05,
             correction='Bonferroni',
             log=False):
    """
    Perform differential gene expression test for groups defined in dgroups.

    Parameters
    ----------
    dgroups (or adata) : dict containing
        groups_names : list, np.ndarray of dtype str
            Array of shape (number of groups) that names the groups.
        groups : list, np.ndarray of dtype str
            Array of shape (number of samples) that names the groups.
    adata : dict, optional
        Data dictionary containing expression matrix and gene names.
    smp : str, optional (default: 'groups')
        Specify the name of the grouping to consider.
    names : str, list, np.ndarray
        Subset of groupnames - e.g. 'C1,C2,C3' or ['C1', 'C2', 'C3'] - in
        dgroups[smp + '_names'] to which comparison shall be restricted.

    Returns
    -------
    ddifftest : dict containing
        zscores : np.ndarray
            Array of shape (number of tests) x (number of genes) storing the
            zscore of the each gene for each test.
        testlabels : np.ndarray of dtype str
            Array of shape (number of tests). Stores the labels for each test.
        genes_sorted : np.ndarray
            Array of shape (number of tests) x (number of genes) storing genes
            sorted according the decreasing absolute value of the zscore.
    """
    # for clarity, rename variable
    groups_names = names
    # if adata is empty, assume that adata dgroups also contains
    # the data file elements
    if not adata:
        sett.m(0, 'testing experimental groups')
        adata = dgroups
    X = adata.X
    if log:
        # Convert X to log scale
        # TODO: treat negativity explicitly
        X = np.abs(X)
        X = np.log(X) / np.log(2)

    # select subset of groups
    groups_names, groups_masks = utils.select_groups(dgroups, groups_names, smp)

    # loop over all masks and compute means, variances and sample numbers
    nr_groups = groups_masks.shape[0]
    nr_genes = X.shape[1]
    means = np.zeros((nr_groups, nr_genes))
    vars = np.zeros((nr_groups, nr_genes))
    ns = np.zeros(nr_groups, dtype=int)
    for imask, mask in enumerate(groups_masks):
        means[imask] = X[mask].mean(axis=0)
        vars[imask] = X[mask].var(axis=0)
        ns[imask] = np.where(mask)[0].size
    sett.m(0, 'testing', smp, 'with', groups_names, 'with sample numbers', ns)
    sett.m(2, 'means', means) 
    sett.m(2, 'variances', vars)

    ddifftest = {'type' : 'difftest'}
    igroups_masks = np.arange(len(groups_masks), dtype=int)
    pairs = list(combinations(igroups_masks, 2))
    pvalues_all = np.zeros((len(pairs), nr_genes))
    zscores_all = np.zeros((len(pairs), nr_genes))
    rankings_geneidcs = np.zeros((len(pairs), nr_genes),dtype=int)
    # each test provides a ranking of genes
    # we store the name of the ranking, i.e. the name of the test, 
    # in the following list
    ddifftest['rankings_names'] = []
    
    # test all combinations of groups against each other
    for ipair, (i,j) in enumerate(pairs):
        # z-scores
        denom = np.sqrt(vars[i]/ns[i] + vars[j]/ns[j])
        zeros = np.flatnonzero(denom==0)
        denom[zeros] = np.nan
        zscores = (means[i] - means[j]) / denom
        # the following is equivalent with 
        # zscores = np.ma.masked_invalid(zscores)
        zscores = np.ma.masked_array(zscores, mask=np.isnan(zscores))
        
        zscores_all[ipair] = zscores
        abs_zscores = np.abs(zscores)

        # p-values
        if False:
            pvalues = 2 * norm.sf(abs_zscores) # two-sided test
            pvalues = np.ma.masked_invalid(pvalues)
            sig_genes = np.flatnonzero(pvalues < 0.05/zscores.shape[0])
            pvalues_all[ipair] = pvalues

        # sort genes according to score
        ranking_geneidcs = np.argsort(abs_zscores)[::-1]        
        # move masked values to the end of the index array
        masked = abs_zscores[ranking_geneidcs].mask
        len_not_masked = len(ranking_geneidcs[masked == False])
        save_masked_idcs = np.copy(ranking_geneidcs[masked])
        ranking_geneidcs[:len_not_masked] = ranking_geneidcs[masked == False]
        ranking_geneidcs[len_not_masked:] = save_masked_idcs
        # write to global rankings_genedics
        rankings_geneidcs[ipair] = ranking_geneidcs
        # names
        ranking_name = groups_names[i] + ' vs '+ groups_names[j]
        ddifftest['rankings_names'].append(ranking_name)

    if False:
        ddifftest['pvalues'] = -np.log10(pvalues_all)

    ddifftest['zscores'] = zscores_all
    ddifftest['rankings_geneidcs'] = rankings_geneidcs
    ddifftest['scoreskey'] = 'zscores'

    return ddifftest

def plot(ddifftest, adata, params=None):
    """
    Plot ranking of genes for all tested comparisons.
    """
    plott.ranking(ddifftest, adata)
    plott.savefig(ddifftest['writekey'])
    if not sett.savefigs and sett.autoshow:
        from ..compat.matplotlib import pyplot as pl
        pl.show()

