'use strict';

var GLClient = angular.module('GLClient', ['GLClient.templates', 'resourceServices',
    'submissionUI', 'GLClientFilters', 'GLClient.themes']).
  config(['$routeProvider', function($routeProvider) {
    var Templates = angular.injector(['GLClient.themes']).get('Templates');

    $routeProvider.
      when('/', {
        templateUrl: Templates.home,
        controller: 'HomeCtrl'
      }).

      when('/about', {
        templateUrl: Templates.about,
        controller: 'PageCtrl',
      }).


      when('/submission', {
        templateUrl: Templates.submission.main,
        controller: 'SubmissionCtrl',
      }).


      when('/status/:tip_id', {
        templateUrl: Templates.status,
        controller: 'StatusCtrl',
      }).


      when('/receiver/preferences', {
        templateUrl: 'views/receiver/preferences.html',
        controller: 'ReceiverPreferencesCtrl'
      }).
      when('/receiver/tips', {
        templateUrl: 'views/receiver/tips.html',
        controller: 'ReceiverTipsCtrl'
      }).


      when('/admin/content', {
        templateUrl: 'views/admin/content.html',
        controller: 'AdminCtrl',
      }).
      when('/admin/contexts', {
        templateUrl: 'views/admin/contexts.html',
        controller: 'AdminCtrl',
      }).
      when('/admin/receivers', {
        templateUrl: 'views/admin/receivers.html',
        controller: 'AdminCtrl',
      }).
      when('/admin/mail', {
        templateUrl: 'views/admin/mail.html',
        controller: 'AdminCtrl',
      }).

      when('/admin/password', {
        templateUrl: 'views/admin/password.html',
        controller: 'AdminCtrl',
      }).

      when('/admin/overview/users', {
        templateUrl: 'views/admin/users_overview.html',
        controller: 'OverviewCtrl',
      }).
      when('/admin/overview/tips', {
        templateUrl: 'views/admin/tips_overview.html',
        controller: 'OverviewCtrl',
      }).
      when('/admin/overview/files', {
        templateUrl: 'views/admin/files_overview.html',
        controller: 'OverviewCtrl',
      }).


      when('/login', {
        templateUrl: 'views/login.html',
        controller: 'LoginCtrl',
      }).

      otherwise({
        redirectTo: '/'
      })
}]);
