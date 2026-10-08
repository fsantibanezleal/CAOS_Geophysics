"""Cold Job-contained independently constructed controls BEFORE new values."""
import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_qr as qr


def run_native_controls(root,job_handle):
    from magnetic_line_survey_runtime import require_job
    from threadpoolctl import threadpool_limits
    require_job(job_handle)
    np,_=core.engines()
    receipts=[]
    with threadpool_limits(limits=1):
        for weighted,correlated in ((False,False),(True,False),(False,True)):
            xyz=np.array([[0.,0.,10.],[5.,0.,12.],[1.,7.,10.],[9.,8.,14.],[4.,3.,11.],[7.,2.,10.]])
            sources=np.array([[1.,1.,-20.],[8.,6.,-20.],[-5.,3.,-20.]])
            if correlated:sources[1]=sources[0]+np.array([1e-8,0.,0.])
            sigma=np.array([1.,2.,.5,3.,1.2,.7]) if weighted else None
            y=np.array([2.,-1.,3.,.5,2.5,-2.]);damping=.0001
            G=1/np.sqrt(np.sum((xyz[:,None,:]-sources[None,:,:])**2,axis=2))
            S=np.std(G,axis=0,ddof=0);A=G/S
            if weighted:A/=sigma[:,None]
            b=y/sigma if weighted else y
            H=np.vstack((A,np.sqrt(damping)*np.eye(3)))
            P=1/np.sqrt(np.sum(A*A,axis=0)+damping);B=H*P
            rhs=np.r_[b,np.zeros(3)];U,s,Vt=np.linalg.svd(H,full_matrices=False)
            oracle=Vt.T@((U.T@rhs)/s)
            for item in (xyz,sources,sigma,y):
                if item is not None:item.flags.writeable=False
            model=core.GlobalOperator(xyz,sources,sigma,job_handle=job_handle)
            import magnetic_line_survey_hp as hp
            actual=qr.augmented_matrix(model,damping,hp.preconditioner(model,damping))
            np.testing.assert_allclose(actual,B,rtol=1e-13)
            state=qr.solve_qr(model,y,damping)
            c=state['scaled_coefficients'];gradient=A.T@(A@c-b)+damping*c
            np.testing.assert_allclose(c,oracle,rtol=1e-7,atol=1e-8)
            np.testing.assert_allclose(state['preconditioner'],P,rtol=1e-13)
            z=np.array([2.,-3.,4.]);u=np.arange(9,dtype=np.float64)-3
            action=actual@z;adjoint=actual.T@u
            np.testing.assert_allclose(action,B@z,rtol=1e-13,atol=1e-13)
            np.testing.assert_allclose(adjoint,B.T@u,rtol=1e-13,atol=1e-13)
            if not np.isclose(u@action,z@adjoint,rtol=1e-13):raise core.SurveyError('custody_mismatch','seal')
            if not np.isclose(np.sum((B@z-rhs)**2),np.sum((A@(P*z)-b)**2)+damping*np.sum((P*z)**2),rtol=1e-13):
                raise core.SurveyError('custody_mismatch','seal')
            _,R=np.linalg.qr(B,mode='reduced');inverse=np.linalg.inv(R)
            condition=float(np.linalg.norm(R,'fro')*np.linalg.norm(inverse,'fro'))
            receipt=state['receipt']
            if not np.isclose(receipt['condition_upper_bound'],condition,rtol=1e-9) or condition<np.linalg.cond(B,2) or \
               not np.isclose(receipt['original_diagnostics']['stationarity_inf'],np.max(np.abs(gradient)),atol=3e-12,rtol=1e-10):
                raise core.SurveyError('custody_mismatch','seal')
            receipts.append(dict(weighted=weighted,correlated=correlated,solve=receipt))
        zero=np.zeros(6);zero.flags.writeable=False
        state=qr.solve_qr(core.GlobalOperator(xyz,sources,job_handle=job_handle),zero,damping)
        if state['receipt']['original_diagnostics']['objective']!=0:raise core.SurveyError('custody_mismatch','seal')
        receipts.append(dict(weighted=False,zero=True,solve=state['receipt']))
    receipt=dict(schema='m03-qr-native-controls/1',epoch=qr.EPOCH,verdict='pass',controls=receipts,
        response_access='independently_constructed_control_only',outer_evaluation_count=0)
    core._write_member(root,'qr-native-controls.json',base.canonical_bytes(receipt))
    return receipt
