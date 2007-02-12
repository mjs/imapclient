Summary: Gnome applet for managing SSH keys stored on removable media
Name: ssh-agent-applet
Version: 0.1
Release: 1
License: GPL
Group: System Environment/Base
Source: %{name}-%{version}.tar.gz
URL: http://freshfoo.com/
BuildRoot: %{_tmppath}/%{name}-%{version}root
BuildArch: noarch
BuildRequires: python
Requires: python >= 2.4
Requires: gnome-python2
Requires: GConf2

%description
ssh-agent-applet is a Gnome applet that allows you to conveniently keep your
ssh key(s) on external media. This means that if your computer is cracked or
stolen, the attacker will not have a copy of private ssh key(s).

Using ssh-agent-appley, your keys are loaded into ssh-agent as soon as you
insert your "key drive" into a USB port. The drive is automatically unmounted
once the key loaded so you can remove it from the USB port immediately.

%prep
%setup -q

%build
%{__python} setup.py build

%install
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --root=$RPM_BUILD_ROOT

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT

%post
gconftool-2 \
    --install-schema-file=%{_sysconfdir}/gconf/schemas/ssh-agent-applet.schema

%files
%defattr(-, root, root)
%doc README AUTHORS COPYING TODO INSTALL
%{_bindir}/ssh-agent-applet
%{_libdir}/bonobo/servers/ssh-agent-applet.server
%{_libdir}/ssh-agent-applet
%{_libdir}/python*/site-packages/sshagentapplet/
%{_sysconfdir}/gconf/schemas/ssh-agent-applet.schema
