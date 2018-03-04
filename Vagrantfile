# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "bento/ubuntu-16.04"

  # config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network :forwarded_port, host: 5555, guest: 8000
  config.vm.network :forwarded_port, host: 1080, guest: 1080

  #config.vm.provision "shell", inline: ""

  config.ssh.forward_agent = true

  # set up synced folders
  config.vm.synced_folder ".", "/src/polefit"

  config.vm.provision "ansible" do |ansible|
    ansible.groups = {
      "siteserver" => ["default"],
    }
    ansible.playbook = "ansible/vagrant.yml"
    ansible.vault_password_file = "ansible/.vaultpass"
    #ansible.verbose='vvvv'
  end

end
