"""Tests for init command and template functionality."""

import json
import tempfile
from pathlib import Path


CORE_PARAM_TEMPLATES = {
    "lammps-vasp",
    "lammps-pwscf",
    "lammps-cp2k",
    "lammps-gaussian",
    "lammps-abacus-pw",
    "lammps-abacus-lcao",
    "lammps-abacus-lcao-dpks",
    "gromacs-gaussian",
    "calypso-vasp",
    "amber-dprc",
    "lammps-vasp-plumed",
    "lammps-vasp-electron-temp",
}

EXPANDED_PARAM_TEMPLATES = CORE_PARAM_TEMPLATES | {
    "lammps-siesta",
    "lammps-pwmat",
    "lammps-cpx",
    "lammps-custom",
    "simplify-none",
    "simplify-vasp",
    "init-bulk-vasp",
    "init-bulk-abacus",
    "init-surf-vasp",
    "init-reaction",
}

EXPANDED_MACHINE_TEMPLATES = {
    "lebesgue-v2",
    "local-shell",
    "slurm",
    "pbs",
    "lsf",
    "ssh-remote",
}


class TestInitCommand:
    """Test the init subcommand functionality."""

    def test_capabilities_includes_init(self, capsys):
        """Verify init is listed in capabilities."""
        from dpgen_lsp import tool

        result = tool.main(["capabilities"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "init" in output["agentCli"]["operations"]

    def test_init_list_all_templates(self, capsys):
        """Test listing all available templates."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--list"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "templates" in output
        templates = output["templates"]
        keys = {t["key"] for t in templates}
        assert EXPANDED_PARAM_TEMPLATES <= keys
        assert EXPANDED_MACHINE_TEMPLATES <= keys

        # Check template structure
        for template in templates:
            assert "key" in template
            assert "kind" in template
            assert "resource" in template
            assert "description" in template
            assert template["kind"] in ["param", "machine"]

    def test_init_list_param_templates(self, capsys):
        """Test listing only param templates."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--list", "--kind", "param"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        templates = output["templates"]
        keys = {t["key"] for t in templates}
        assert EXPANDED_PARAM_TEMPLATES <= keys
        assert all(t["kind"] == "param" for t in templates)

    def test_init_list_machine_templates(self, capsys):
        """Test listing only machine templates."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--list", "--kind", "machine"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        templates = output["templates"]
        keys = {t["key"] for t in templates}
        assert EXPANDED_MACHINE_TEMPLATES <= keys
        assert all(t["kind"] == "machine" for t in templates)

    def test_init_create_param_file(self):
        """Test creating a param.json file from template."""
        from dpgen_lsp import tool

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            result = tool.main(["init", "--template", "lammps-vasp", str(out)])
            assert result == 0
            assert out.exists()

            data = json.loads(out.read_text())
            assert "type_map" in data
            assert "mass_map" in data
            assert "init_data_sys" in data

    def test_init_create_machine_file(self):
        """Test creating a machine.json file from template."""
        from dpgen_lsp import tool

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "machine.json"
            result = tool.main(["init", "--template", "lebesgue-v2", str(out)])
            assert result == 0
            assert out.exists()

            data = json.loads(out.read_text())
            assert "api_version" in data
            assert "train" in data
            assert "model_devi" in data
            assert "fp" in data

    def test_init_stdout_mode(self, capsys):
        """Test outputting template to stdout."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--template", "lammps-vasp", "--stdout"])
        assert result == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "type_map" in data

    def test_init_prevent_overwrite(self, capsys):
        """Test that init refuses to overwrite existing file without --force."""
        from dpgen_lsp import tool

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            out.write_text('{"existing": "data"}')

            result = tool.main(["init", "--template", "lammps-vasp", str(out)])
            assert result == 1

            # Verify original content preserved
            data = json.loads(out.read_text())
            assert data == {"existing": "data"}

    def test_init_force_overwrite(self):
        """Test that --force allows overwriting existing file."""
        from dpgen_lsp import tool

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            out.write_text('{"existing": "data"}')

            result = tool.main(["init", "--template", "lammps-vasp", "--force", str(out)])
            assert result == 0

            # Verify new content
            data = json.loads(out.read_text())
            assert "type_map" in data
            assert "existing" not in data

    def test_init_nonexistent_template(self, capsys):
        """Test behavior with invalid template name."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--template", "nonexistent", "param.json"])
        assert result == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert "not found" in output["error"].lower()

    def test_init_all_param_templates_readable(self):
        """Verify all param templates can be read and are valid JSON."""
        from dpgen_lsp import tool
        from dpgen_lsp import templates as template_library

        templates = [t["key"] for t in template_library.list_templates(kind="param")]

        for template_name in templates:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / f"{template_name}.json"
                result = tool.main(["init", "--template", template_name, str(out)])
                assert result == 0, f"Failed to create {template_name}"
                assert out.exists(), f"File not created for {template_name}"

                # Verify valid JSON
                data = json.loads(out.read_text())
                assert isinstance(data, dict), f"{template_name} is not a dict"

    def test_init_requires_template_for_file(self, capsys):
        """Test that init requires --template when creating a file."""
        from dpgen_lsp import tool

        result = tool.main(["init", "param.json"])
        assert result == 1

        captured = capsys.readouterr()
        assert "template" in captured.err.lower()

    def test_init_requires_template_for_stdout(self, capsys):
        """Test that init requires --template when using --stdout."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--stdout"])
        assert result == 1

        captured = capsys.readouterr()
        assert "template" in captured.err.lower()

    def test_init_requires_path_for_file(self, capsys):
        """Test that init requires output path when not using --list or --stdout."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--template", "lammps-vasp"])
        assert result == 1

        captured = capsys.readouterr()
        assert "path" in captured.err.lower()

    def test_init_default_template(self, capsys):
        """Test that lammps-vasp is marked as default template."""
        from dpgen_lsp import tool

        result = tool.main(["init", "--list"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        default_templates = [t for t in output["templates"] if t.get("default") is True]
        assert len(default_templates) == 1
        assert default_templates[0]["key"] == "lammps-vasp"


class TestTemplateLibrary:
    """Test the template library functions directly."""

    def test_list_templates_all(self):
        """Test listing all templates."""
        from dpgen_lsp import templates

        result = templates.list_templates()
        keys = {t["key"] for t in result}
        assert EXPANDED_PARAM_TEMPLATES <= keys
        assert EXPANDED_MACHINE_TEMPLATES <= keys
        assert all("key" in t for t in result)
        assert all("kind" in t for t in result)
        assert all("resource" in t for t in result)

    def test_list_templates_by_kind(self):
        """Test filtering templates by kind."""
        from dpgen_lsp import templates

        param_templates = templates.list_templates(kind="param")
        param_keys = {t["key"] for t in param_templates}
        assert EXPANDED_PARAM_TEMPLATES <= param_keys
        assert all(t["kind"] == "param" for t in param_templates)

        machine_templates = templates.list_templates(kind="machine")
        machine_keys = {t["key"] for t in machine_templates}
        assert EXPANDED_MACHINE_TEMPLATES <= machine_keys
        assert all(t["kind"] == "machine" for t in machine_templates)

    def test_get_template(self):
        """Test getting a specific template."""
        from dpgen_lsp import templates

        template = templates.get_template("lammps-vasp")
        assert template is not None
        assert template["key"] == "lammps-vasp"
        assert template["kind"] == "param"
        assert template["fp_style"] == "vasp"
        assert template["md_engine"] == "lammps"

    def test_get_template_not_found(self):
        """Test behavior when template doesn't exist."""
        from dpgen_lsp import templates

        result = templates.get_template("nonexistent")
        assert result is None

    def test_read_template(self):
        """Test reading template content."""
        from dpgen_lsp import templates

        content = templates.read_template("lammps-vasp")
        assert content is not None

        # Should be valid JSON
        data = json.loads(content)
        assert "type_map" in data

    def test_read_template_not_found(self):
        """Test read_template with invalid template."""
        from dpgen_lsp import templates

        result = templates.read_template("nonexistent")
        assert result is None

    def test_write_template(self):
        """Test writing template to file."""
        from dpgen_lsp import templates

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            result = templates.write_template("lammps-vasp", out)

            assert result["success"] is True
            assert out.exists()

            data = json.loads(out.read_text())
            assert "type_map" in data

    def test_write_template_no_overwrite(self):
        """Test write_template refuses to overwrite by default."""
        from dpgen_lsp import templates

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            out.write_text('{"existing": "data"}')

            result = templates.write_template("lammps-vasp", out)

            assert result["success"] is False
            assert "already exists" in result["error"].lower()

            # Verify original content preserved
            data = json.loads(out.read_text())
            assert data == {"existing": "data"}

    def test_write_template_with_overwrite(self):
        """Test write_template with overwrite flag."""
        from dpgen_lsp import templates

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            out.write_text('{"existing": "data"}')

            result = templates.write_template("lammps-vasp", out, overwrite=True)

            assert result["success"] is True

            data = json.loads(out.read_text())
            assert "type_map" in data
            assert "existing" not in data

    def test_write_template_invalid(self):
        """Test write_template with invalid template."""
        from dpgen_lsp import templates

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "param.json"
            result = templates.write_template("nonexistent", out)

            assert result["success"] is False
            assert "not found" in result["error"].lower()

    def test_template_index_structure(self):
        """Verify index.json has correct structure."""
        from dpgen_lsp import templates

        index = templates._load_index()

        assert "$schema" in index
        assert "upstream" in index
        assert "fetched" in index
        assert "templates" in index

        assert isinstance(index["templates"], list)
        assert len(index["templates"]) > 0

    def test_template_resources_exist(self):
        """Verify all template resource files exist."""
        from dpgen_lsp import templates

        all_templates = templates.list_templates()

        for template in all_templates:
            resource_path = templates._TEMPLATES_DIR / template["resource"]
            assert resource_path.exists(), f"Missing resource: {template['resource']}"
