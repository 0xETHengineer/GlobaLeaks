// In here go angular.js filters
// http://docs.angularjs.org/guide/dev_guide.templates.filters.creating_filters
//
angular.module('GLClientFilters', []).
  filter('required-filter', function() {
    return function(input) {
      if (input) {
        return 'required';
      } else {
        return '';
      }
    }
}).
  filter('field-type-filter', function() {
    return function(input) {
      if (input == "string") {
        return 'text';
      } else {
        return input;
      }
    }
}).
  filter('translate', ['$cookies', function($cookies) {
    return function(input) {
      var hash = md5(input);
      return translations[hash][$cookies['language']];
    }
}]);
