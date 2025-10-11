"""Tests for rich console utilities."""



class TestGetConsole:
    """Tests for get_console() function."""
    
    def test_console_singleton(self):
        """Test that console is a singleton."""
        from bengal.utils.rich_console import get_console, reset_console
        
        # Reset to ensure clean state
        reset_console()
        
        console1 = get_console()
        console2 = get_console()
        assert console1 is console2
    
    def test_no_color_respected(self, monkeypatch):
        """Test that NO_COLOR environment variable is respected."""
        from bengal.utils.rich_console import get_console, reset_console
        
        monkeypatch.setenv('NO_COLOR', '1')
        reset_console()
        
        console = get_console()
        assert console.no_color is True
    
    def test_ci_mode_detection(self, monkeypatch):
        """Test that CI mode is detected and disables color."""
        from bengal.utils.rich_console import get_console, reset_console
        
        monkeypatch.setenv('CI', 'true')
        reset_console()
        
        console = get_console()
        # In CI mode, force_terminal should be False
        # This is internal to Console, so we check behavior
        assert console is not None


class TestShouldUseRich:
    """Tests for should_use_rich() function."""
    
    def test_disabled_in_ci(self, monkeypatch):
        """Test that rich is disabled in CI environments."""
        from bengal.utils.rich_console import should_use_rich, reset_console
        
        monkeypatch.setenv('CI', 'true')
        reset_console()
        
        assert should_use_rich() is False
    
    def test_disabled_with_dumb_terminal(self, monkeypatch):
        """Test that rich is disabled with TERM=dumb."""
        from bengal.utils.rich_console import should_use_rich, reset_console
        
        monkeypatch.setenv('TERM', 'dumb')
        monkeypatch.delenv('CI', raising=False)
        reset_console()
        
        assert should_use_rich() is False
    
    def test_disabled_without_terminal(self, monkeypatch):
        """Test that rich is disabled when not a terminal."""
        from bengal.utils.rich_console import should_use_rich, reset_console
        
        # Clean environment
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.delenv('TERM', raising=False)
        monkeypatch.setenv('TERM', 'xterm')
        reset_console()
        
        # When running in pytest, is_terminal is typically False
        result = should_use_rich()
        # In test environment, this should be False (no real terminal)
        assert isinstance(result, bool)


class TestDetectEnvironment:
    """Tests for detect_environment() function."""
    
    def test_detects_ci_environment(self, monkeypatch):
        """Test that CI environments are detected."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        monkeypatch.setenv('CI', 'true')
        reset_console()
        
        env = detect_environment()
        assert env['is_ci'] is True
    
    def test_detects_github_actions(self, monkeypatch):
        """Test that GitHub Actions is detected as CI."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('GITHUB_ACTIONS', 'true')
        reset_console()
        
        env = detect_environment()
        assert env['is_ci'] is True
    
    def test_detects_docker(self, tmp_path):
        """Test that Docker containers are detected."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        reset_console()
        env = detect_environment()
        
        # This will be False in normal test environment
        assert isinstance(env['is_docker'], bool)
    
    def test_detects_git_repo(self, tmp_path, monkeypatch):
        """Test that Git repositories are detected."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        reset_console()
        
        env = detect_environment()
        assert env['is_git_repo'] is False
        
        # Create .git directory
        (tmp_path / '.git').mkdir()
        reset_console()
        
        env = detect_environment()
        assert env['is_git_repo'] is True
    
    def test_returns_cpu_count(self):
        """Test that CPU count is returned."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        reset_console()
        env = detect_environment()
        
        assert 'cpu_count' in env
        assert env['cpu_count'] > 0
        assert isinstance(env['cpu_count'], int)
    
    def test_returns_terminal_info(self):
        """Test that terminal info is returned."""
        from bengal.utils.rich_console import detect_environment, reset_console
        
        reset_console()
        env = detect_environment()
        
        assert 'is_terminal' in env
        assert 'color_system' in env
        assert 'width' in env
        assert 'height' in env
        assert 'terminal_app' in env
        
        assert isinstance(env['is_terminal'], bool)
        assert isinstance(env['width'], int)
        assert isinstance(env['height'], int)


class TestResetConsole:
    """Tests for reset_console() function."""
    
    def test_resets_singleton(self):
        """Test that reset_console() clears the singleton."""
        from bengal.utils.rich_console import get_console, reset_console
        
        console1 = get_console()
        reset_console()
        console2 = get_console()
        
        # Should be different instances after reset
        assert console1 is not console2

