
chrome.runtime.onMessage.addListener(
    function(request, sender, sendResponse) {
        console.log("clicked button")
      if( request.message === "clicked_browser_action" ) {
        document.body.style.backgroundColor = "green"; 
        var string = document.documentElement.innerHTML; 
        console.log(string)
      }
    }
  );
  console.log("Loaded content script")
  // document.body.style.backgroundColor = "red";

// export function getHtml() {
//       console.log(document,"documentssss")
//     var string = document.documentElement.innerHTML;
//     console.log(string)
// }
export function getHtml(completion) {
    // var queryInfo = {
    //     active: true,
    //     currentWindow: true
    // };
    // chrome.tabs.query(queryInfo, (tabs) => {
    //     var tab = tabs[0];
    //     var url = tab.url;
    //     console.log("urlllll",url,tab)
    //     // document.getElementById('url').innerHTML = url;
    // });
    chrome.tabs.executeScript( {
        code: '(' + modifyDOM + ')();' //argument here is a string but function.toString() returns function's code
    }, function(selection) {
        completion(selection.toString());
    });
}
function modifyDOM() {
    //You can play with your DOM here or check URL against your regex
    var content = document.body.outerHTML;
    return content;
}