project(
	'pywayfire',
	version: '3.2',
	license: 'MIT',
	meson_version: '>=0.55',
)

dependency('wayfire', required: false)
pip = find_program('pip')

message(run_command(pip, 'install', '.', '--break-system-packages', check: true).stdout().strip())
