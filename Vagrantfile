# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "ubuntu/trusty64"

  config.vm.network "forwarded_port", guest: 80, host: 8080

  #config.vm.provision "shell", inline: ""

  config.vm.provision "ansible" do |ansible|
    ansible.groups = {
      "siteserver" => ["default"],
    }
    ansible.playbook = "provisioning/playbook.yml"
    #ansible.ask_vault_pass = true
    #ansible.verbose='vvvv'
  end

end
