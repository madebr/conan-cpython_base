from conans import ConanFile, AutoToolsBuildEnvironment, tools
import os


class CPythonBaseConan(ConanFile):
    name = "cpython_base"
    version = "3.7.1"
    description = "The Python programming language"
    topics = ("conan", "python", "programming", "language", "scripting")
    url = "https://github.com/bincrafters/conan-cpython_base"
    homepage = "https://www.python.org"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "PSF"
    no_copy_sources = True
    base_options = {  # FIXME: add curses readline
        "shared": [True, False],
        "fPIC": [True, False],
        "optimizations": [True, False],
        "lto": [True, False],
        "bz2": [True, False],
        "ctypes": [True, False],
        "decimal": [True, False],
        "dbm": [True, False],
        "expat": [True, False],
        "gdbm": [True, False],
        "lzma": [True, False],
        "nis": [True, False],
        "sqlite3": [True, False],
        "tcltk": [True, False],
        "uuid": [True, False],
        "ipv6": [True, False],
    }
    base_default_options = {
        "shared": False,
        "fPIC": True,
        "optimizations": False,
        "lto": False,
        "ipv6": True,
        "bz2": True,
        "ctypes": True,
        "dbm": True,
        "decimal": True,
        "expat": True,
        "gdbm": True,
        "lzma": True,
        "nis": True,
        "sqlite3": True,
        "tcltk": True,
        "uuid": True,
    }
    base_requirements = "OpenSSL/1.1.1@conan/stable",
    _source_subfolder = "sources"

    cpython_base_fail_on_error = False
    python_for_regen = None

    def get_option(self, option):
        if not self.cpython_base_fail_on_error:
            return getattr(self.options, option) if option in self.options.fields else False
        return getattr(self.options, option)

    @property
    def debug_build(self):
        if "build_type" in self.settings.fields:
            return self.settings.build_type == "Debug"
        else:
            return False

    @property
    def major_minor_version(self):
        return self.version[:self.version.rfind(".")]

    def config_options(self):
        if "compiler" in self.settings.fields:
            if hasattr(self.settings.compiler, "libcxx"):
                del self.settings.compiler.libcxx
        if "os" in self.settings.fields:
            if self.settings.os in ("Windows", "Macos"):
                if self.get_option("nis"):
                    del self.options.nis
        if self.get_option("shared"):
            del self.options.fPIC

    @property
    def is_mingw(self):
        try:
            return self.settings.os == "Windows" and self.settings.compiler == "gcc"
        except AttributeError:
            return self.settings.os_build == "Windows" and self.settings.compiler == "gcc"

    def base_options_requirements(self, requires):
        if self.options.bz2:
            requires("bzip2/1.0.6@conan/stable")
        if self.options.ctypes:
            requires("libffi/3.3-rc0@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.dbm:
            requires("libdb/5.3.28@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.decimal:
            requires("mpdecimal/2.4.2@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.expat:
            requires("expat/2.2.5@bincrafters/stable")
        if self.options.gdbm:
            requires("gdbm/1.18.1@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.lzma:
            requires("lzma/5.2.3@bincrafters/stable")
        if self.options.nis:
            requires("libnsl/1.2.0@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.sqlite3:
            requires("sqlite3/3.25.3@bincrafters/stable")
        if self.options.tcltk:
            requires("tcl/8.6.8@bincrafters/stable")
            requires("tk/8.6.8@maarten/testing")  # FIXME: submit to bincrafters
        if self.options.uuid:
            requires("libuuid/1.0.3@bincrafters/stable")

    def base_source(self):
        source_url = "https://www.python.org/ftp/python/{0}/Python-{0}.tgz".format(self.version)
        sha256sum = "36c1b81ac29d0f8341f727ef40864d99d8206897be96be73dc34d4739c9c9f06"
        tools.get(source_url, sha256=sha256sum)
        extracted_dir = "Python-{0}".format(self.version)
        os.rename(extracted_dir, self._source_subfolder)
        # fix library name of mpdecimal
        tools.replace_in_file(os.path.join(self.source_folder, self._source_subfolder, "setup.py"),
                              ":libmpdec.so.2", "libmpdec")
        tools.replace_in_file(os.path.join(self.source_folder, self._source_subfolder, "setup.py"),
                              "libraries = ['libmpdec']", "libraries = ['mpdec']")

        # on building x86 python on x86_64: readlink is just fine
        tools.replace_in_file(os.path.join(self.source_folder, self._source_subfolder, "configure"),
                              "as_fn_error $? \"readelf for the host is required for cross builds\"",
                              "# as_fn_error $? \"readelf for the host is required for cross builds\"")

        makefile = os.path.join(self.source_folder, self._source_subfolder, "Makefile.pre.in")
        tools.replace_in_file(makefile,
                              "@OPT@",
                              "@OPT@ @CFLAGS@")

    def build_autotools(self):
        autotools = AutoToolsBuildEnvironment(self)
        autotools.target = autotools.host

        if self.get_option("uuid"):
            autotools.include_paths += ["{}/uuid".format(d) for d in self.deps_cpp_info["libuuid"].includedirs]
        args = [
            "--enable-shared" if self.get_option("shared") else "--disable-shared",
            "--with-gcc", "--without-icc",
            "--with-system-expat" if self.get_option("expat") else "--without-system-expat",
            "--with-system-libmpdec" if self.get_option("decimal") else "--without-system-libmpdec",
            "--enable-optimizations" if self.get_option("optimizations") else "--disable-optimizations",
            "--with-lto" if self.get_option("lto") else "--without-lto",
            "--with-openssl={}".format(self.deps_cpp_info["OpenSSL"].rootpath),
        ]
        if self.debug_build:
            args.extend(["--with-pydebug", "--with-assertions"])
        else:
            args.extend(["--without-pydebug", "--without-assertions"])
        if self.get_option("tcltk"):
            tcltk_includes = []
            tcltk_libs = []
            for dep in ("tcl", "tk", "zlib"):
                tcltk_includes += ["-I{}".format(d) for d in self.deps_cpp_info[dep].includedirs]
                tcltk_libs += ["-l{}".format(lib) for lib in self.deps_cpp_info[dep].libs]
            args.extend([
                "--with-tcltk-includes={}".format(" ".join(tcltk_includes)),
                "--with-tcltk-libs={}".format(" ".join(tcltk_libs)),
            ])
        args.append("--enable-ipv6" if self.get_option("ipv6") else "--disable-ipv6")
        env_vars = {
            "PKG_CONFIG": os.path.abspath("pkg-config"),
        }
        if self.python_for_regen:
            env_vars["PYTHON_FOR_REGEN"] = self.python_for_regen
        if self.settings.compiler in ("gcc", "clang"):
            if self.settings.arch == "x86":
                # fix finding PLATFORM_TRIPLET (used for e.g. extensions of native python modules)
                env_vars["CPPFLAGS"] = "-m32"

        with tools.environment_append(env_vars):
            autotools.configure(configure_dir=os.path.join(self.source_folder, self._source_subfolder), args=args)
            autotools.make()

    def package_autotools(self):
        with tools.chdir(self.build_folder):
            env_build = AutoToolsBuildEnvironment(self)
            env_build.make(args=["install", "-j1"])

    def build_msvc(self):
        with tools.chdir(os.path.join(self._source_subfolder, "PCBuild")):
            build_type = self.settings.build_type
            arch = "x64" if self.settings.arch == "x86_64" else "Win32"
            self.run("build.bat -c {build_type} -p {arch}".format(build_type=build_type, arch=arch))

    def package_msvc(self):
        raise NotImplemented()
