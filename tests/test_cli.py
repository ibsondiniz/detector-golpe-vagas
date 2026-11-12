import json

from detector_golpe.cli import main


def test_cli_prints_one_line_per_ad(tmp_path, capsys):
    f = tmp_path / "vagas.json"
    f.write_text(json.dumps([
        {"id": "a", "title": "Digitador", "description": "Curso obrigatório. Envie o CPF pelo WhatsApp."},
        {"id": "b", "name": "Dev Python", "careerPageName": "Exemplo SA", "description": "Vaga remota para dev Python. " * 20},
    ]), encoding="utf-8")
    main([str(f)])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("a | SUSPEITA | G1")
    assert lines[1] == "b | ok | "
