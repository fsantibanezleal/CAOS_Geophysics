"""Output custody refusal before computation/rendering or mkdir."""

from pathlib import Path

import pytest
import gravity_processing as corrections
import gravity_transforms as transforms


@pytest.mark.parametrize('lane',['correction','transform'])
@pytest.mark.parametrize('kind',['ignored-own-repo','other-repo','relative'])
def test_output_must_be_explicit_absolute_external_to_every_repository(tmp_path,monkeypatch,capsys,lane,kind):
    monkeypatch.chdir(tmp_path)
    own=tmp_path/'product'; own.mkdir(); (own/'.git').write_text('gitdir: protected-test-marker')
    other=tmp_path/'other-product'; other.mkdir(); (other/'.git').mkdir()
    monkeypatch.setattr(corrections,'__file__',str(own/'data-pipeline/gravity_processing.py'))
    monkeypatch.setattr(transforms,'ROOT',own)
    output=(own/'data/raw/gravity-m01' if lane=='correction' else own/'data/raw/gravity-m01-transforms')/'forbidden'
    if kind=='other-repo': output=other/'ignored/output'
    elif kind=='relative': output=Path('relative-private-output')
    if lane=='correction':
        assert corrections.main(['--input',str(tmp_path/'not-read.json'),'--output-dir',str(output)])==2
        assert 'external' in capsys.readouterr().err
    else:
        request={'declared':'storage refusal control, not science'}
        result={'provenance':{'request_sha256':corrections.digest(request)}}
        with pytest.raises(corrections.GravityContractError,match='external'):
            transforms.export_bundle(request,result,output)
    if kind!='relative': assert not output.exists()
    assert not list(tmp_path.rglob('gravity-result.json'))
    assert not list(tmp_path.rglob('.m01-transform-*'))
