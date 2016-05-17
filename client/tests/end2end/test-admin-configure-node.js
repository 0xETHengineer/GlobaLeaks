describe('adming configure node', function() {
  it('should configure node', function(done) {
    browser.setLocation('admin/advanced_settings');

    // simplify the configuration in order to simplfy initial tests
    element(by.model('admin.node.disable_security_awareness_badge')).click();

    // enable all receivers to postpone and delete tips
    element(by.model('admin.node.can_postpone_expiration')).click();
    element(by.model('admin.node.can_delete_submission')).click();

    // enable experimental featuress that by default are disabled
    element(by.model('admin.node.enable_experimental_features')).click();

    // save settings
    element(by.css('[data-ng-click="updateNode(admin.node)"]')).click().then(function() {
      done();
    });
  });
});
