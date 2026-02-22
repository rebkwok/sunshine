    document.body.addEventListener("showAlert", function(evt){
    console.log(evt);
    if (evt.detail.level === "success") {
       vNotify.success({text: evt.detail.message, title: evt.detail.title, position: 'bottomLeft'});   
    }
    else if (evt.detail.level === "warning") {
       vNotify.warning({text: evt.detail.message, title: evt.detail.title, position: 'bottomLeft'});   
    }
    else if (evt.detail.level === "error") {
       vNotify.error({text: evt.detail.message, title: evt.detail.title, position: 'bottomLeft'});   
    }
    else {
       vNotify.info({text: evt.detail.message, title: evt.detail.title, position: 'bottomLeft'});   
    }
})