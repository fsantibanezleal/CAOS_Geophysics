"""One global sparse incidence solve, not independent tile gauges or Ridge.

Independent graph connectivity proves incidence rank after one lexicographic
tie gauge per component. A conservative spanning-tree condition bound keeps
the original 1e12 ceiling; it is not relabelled as an observed SVD condition.
"""
from __future__ import annotations

import math
from pathlib import Path
import sqlite3

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io


def solve_incidence(edges, weights_policy, *, temp_root, job_handle=None, edge_limit=8000000):
    """Stream admitted fold constraints; preserve empty/disconnected negatives.

    The caller is the owner-produced fold crossover stage, not a serialized
    Python iterator. No untrusted SQLite or executable archive is opened.
    Every edge is scanned and counted before importing numerical engines.
    """
    if type(edge_limit) is not int or not 1<=edge_limit<=8000000 or weights_policy not in ('unweighted','admitted_inverse_variance'):
        raise core.SurveyError('invalid_contract','crossover')
    if job_handle is not None:
        from magnetic_line_survey_runtime import require_job
        require_job(job_handle)
    with io.scratch_directory(temp_root) as directory:
        directory = Path(directory)
        db = sqlite3.connect(directory/'incidence.sqlite3')
        try:
            db.execute('PRAGMA cache_size=-8192')
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+str(directory).replace("'","''")+"'")
            db.execute('PRAGMA max_page_count=8388608')
            db.execute('CREATE TABLE edges (sequence INTEGER PRIMARY KEY,flight TEXT,tie TEXT,difference REAL,weight REAL)')
            parent,roles,degree = {},{},{}

            def representative(line):
                while parent[line]!=line:
                    parent[line]=parent[parent[line]]
                    line=parent[line]
                return line

            count = 0
            for row in edges:
                count += 1
                if count>edge_limit or count>4096 and job_handle is None:
                    raise core.SurveyError('resource_refused','crossover')
                if type(row) is not dict or set(row)!={'flight','tie','difference_nT','variance_nT2'}:
                    raise core.SurveyError('invalid_contract','crossover')
                difference,variance = row['difference_nT'],row['variance_nT2']
                if type(difference) not in (int,float) or not math.isfinite(difference) or \
                   variance is not None and (type(variance) not in (int,float) or not math.isfinite(variance) or variance<=0):
                    raise core.SurveyError('invalid_contract','crossover')
                if weights_policy=='admitted_inverse_variance' and variance is None:
                    raise core.SurveyError('metadata_ineligible','crossover')
                weight = 1. if weights_policy=='unweighted' else 1/math.sqrt(variance)
                if not math.isfinite(weight) or weight<=0 or not math.isfinite(weight*weight) or weight*weight==0 or \
                   not math.isfinite(weight*difference) or difference!=0 and weight*difference==0:
                    raise core.SurveyError('metadata_ineligible','crossover')
                for key in ('flight','tie'):
                    line = row[key]
                    if type(line) is not str or not base.ID_PATTERN.fullmatch(line) or (line in roles and roles[line]!=key):
                        raise core.SurveyError('invalid_contract','crossover')
                    roles[line]=key
                    parent.setdefault(line,line)
                    degree[line]=degree.get(line,0)+1
                    if len(parent)>65536 or len(parent)>32 and job_handle is None:
                        raise core.SurveyError('resource_refused','crossover')
                a,b = representative(row['flight']),representative(row['tie'])
                if a!=b:
                    parent[max(a,b)]=min(a,b)
                db.execute('INSERT INTO edges VALUES (?,?,?,?,?)',(count-1,row['flight'],row['tie'],difference,weight))
                if count%4096==0:
                    db.commit()
            db.commit()
            if count==0:
                raise core.SurveyError('metadata_ineligible','crossover')
            if (count>4096 or len(parent)>32) and job_handle is None:
                raise core.SurveyError('resource_refused','crossover')
            # CSR + possible int32 copies, rhs/residual/action vectors, graph
            # summaries and native-library reserve; no N*M or M*M allocation.
            buffer_bound = 64*count+512*len(parent)+134217728+1073741824
            if buffer_bound>core.RSS_LIMIT:
                raise core.SurveyError('resource_refused','crossover')
            groups = {}
            for line in sorted(parent):
                groups.setdefault(representative(line),[]).append(line)
            components,gauges = [],set()
            group_of = {}
            for number,group in enumerate(groups.values()):
                ties = [line for line in group if roles[line]=='tie']
                if not ties:
                    raise core.SurveyError('metadata_ineligible','crossover')
                gauge = min(ties)
                gauges.add(gauge)
                component = dict(component_id=f'C{number:03d}',line_ids=group,gauge_line_id=gauge,
                    rank=len(group)-1,absolute_datum=False,rank_method='incidence_connected_component',
                    condition_upper_bound=None)
                components.append(component)
                for line in group:
                    group_of[line]=number
            extremes = [[math.inf,0.] for _ in components]
            for flight,weight in db.execute('SELECT flight,weight FROM edges ORDER BY sequence'):
                interval = extremes[group_of[flight]]
                interval[0],interval[1]=min(interval[0],weight),max(interval[1],weight)
            for component,(minimum,maximum) in zip(components,extremes,strict=True):
                k=len(component['line_ids'])
                bound = math.sqrt(2*max(degree[line] for line in component['line_ids']))*math.sqrt(k*(k-1))*maximum/minimum
                if not math.isfinite(bound) or bound>1e12:
                    raise core.SurveyError('metadata_ineligible','crossover')
                component['condition_upper_bound']=bound
                component['rank_receipt_sha256']=base.digest(component)
            free = [line for line in sorted(parent) if line not in gauges]
            index = {line:number for number,line in enumerate(free)}
            np,_ = core.engines()
            from scipy.sparse import csr_matrix
            from scipy.sparse.linalg import lsmr
            from threadpoolctl import threadpool_limits
            data = np.empty(2*count,dtype=np.float64)
            columns = np.empty(2*count,dtype=np.int64)
            pointer = np.empty(count+1,dtype=np.int64)
            rhs = np.empty(count,dtype=np.float64)
            used = 0
            pointer[0]=0
            for sequence,flight,tie,difference,weight in db.execute('SELECT * FROM edges ORDER BY sequence'):
                entries = [(index[line],sign*weight) for line,sign in ((flight,1),(tie,-1)) if line not in gauges]
                for column,value in sorted(entries):
                    columns[used],data[used]=column,value
                    used += 1
                pointer[sequence+1]=used
                rhs[sequence]=difference*weight
            matrix = csr_matrix((data[:used],columns[:used],pointer),shape=(count,len(free)))
            try:
                with threadpool_limits(limits=1),np.errstate(over='raise',divide='raise',invalid='raise'):
                    # No damping/normal equations. This is incidence calibration,
                    # separate from the equivalent-source regularization lambda.
                    output = lsmr(matrix,rhs,damp=0.,atol=1e-12,btol=1e-12,conlim=1e12,maxiter=2000,show=False,x0=None)
                    values = output[0]
                    if int(output[1]) not in (0,1,2,4,5) or not np.isfinite(values).all() or \
                       any(not math.isfinite(float(value)) or value<0 for value in output[3:]) or output[6]>1e12:
                        raise core.SurveyError('nonconverged','crossover')
                    # Independent graph action, not the recurrence normar or
                    # the same sparse-matrix transpose called a second time.
                    gradient = [0.]*len(free)
                    rhs_terms = [0.]*len(free)
                    model_terms = [0.]*len(free)
                    compensation = [[0.]*len(free) for _ in range(3)]
                    residuals = np.empty(count,dtype=np.float64)
                    offsets = {line:float(values[index[line]]) if line in index else 0. for line in sorted(parent)}

                    def accumulate(total,comp,column,increment):
                        adjusted = increment-comp[column]
                        new = total[column]+adjusted
                        comp[column]=(new-total[column])-adjusted
                        total[column]=new

                    for sequence,flight,tie,difference,weight in db.execute('SELECT * FROM edges ORDER BY sequence'):
                        prediction = offsets[flight]-offsets[tie]
                        residuals[sequence]=difference-prediction
                        for line,sign in ((flight,1),(tie,-1)):
                            if line in index:
                                column=index[line]
                                w2=sign*weight*weight
                                for total,comp,value in zip((gradient,rhs_terms,model_terms),compensation,
                                                           (prediction-difference,difference,prediction),strict=True):
                                    increment=w2*value
                                    if not math.isfinite(increment) or value!=0 and increment==0:
                                        raise core.SurveyError('nonconverged','crossover')
                                    accumulate(total,comp,column,increment)
                    if any(not math.isfinite(value) for total in (gradient,rhs_terms,model_terms) for value in total):
                        raise core.SurveyError('nonconverged','crossover')
                    denominator = max(max(map(abs,rhs_terms)),max(map(abs,model_terms)))
                    absolute = max(map(abs,gradient))
                    relative = absolute/denominator if denominator>0 else (0. if absolute==0 else math.inf)
                    if not np.isfinite(residuals).all() or not math.isfinite(relative) or relative>1e-9:
                        raise core.SurveyError('nonconverged','crossover')
            except (FloatingPointError,OverflowError):
                raise core.SurveyError('nonconverged','crossover') from None
            residuals.flags.writeable=False
            return dict(offsets=offsets,components=components,residuals=residuals,common_relative_gauge=len(components)==1,
                istop=int(output[1]),iterations=int(output[2]),stationarity_relative=relative,rows=count,
                buffer_bound_bytes=buffer_bound,field_acceptance='unresolved')
        except sqlite3.Error:
            raise core.SurveyError('resource_refused','crossover') from None
        finally:
            db.close()
